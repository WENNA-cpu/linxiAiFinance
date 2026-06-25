"""
随机森林 v2.0 训练 — AKShare 估值 + 扩展特征
特征：波动率、换手率、PE分位、PB分位、成交量变化率、振幅
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score, recall_score
from sklearn.model_selection import train_test_split

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from training.config import (
    RF_FORWARD_DAYS,
    RF_MODEL_PATH,
    RF_N_ESTIMATORS,
    RF_V2_COMPARE_REPORT,
    RF_V2_EVAL_REPORT,
    RF_V2_FEATURE_NAMES,
    RF_V2_IMPORTANCE_PLOT,
    RF_V2_MODEL_PATH,
    STOCK_LIMIT,
    TRAIN_YEARS_V2,
)
from training.data_fetch import prepare_training_data
from training.train_rf import FEATURE_NAMES as RF_V1_FEATURE_NAMES
from training.train_rf import LABEL_NAMES, engineer_features


def engineer_features_v2(group: pd.DataFrame, forward_days: int = RF_FORWARD_DAYS) -> pd.DataFrame:
    g = group.sort_values("trade_date").copy()
    g["close"] = pd.to_numeric(g["close"], errors="coerce")
    g["vol"] = pd.to_numeric(g["vol"], errors="coerce")
    g["pe"] = pd.to_numeric(g.get("pe"), errors="coerce")
    g["pb"] = pd.to_numeric(g.get("pb"), errors="coerce")
    g["turnover_rate"] = pd.to_numeric(g.get("turnover_rate"), errors="coerce")

    g["return"] = g["close"].pct_change()
    g["volatility"] = g["return"].rolling(20).std()
    g["volume_change_rate"] = g["vol"].pct_change().replace([np.inf, -np.inf], np.nan)

    if "pe_percentile" in g.columns:
        g["pe_percentile"] = pd.to_numeric(g["pe_percentile"], errors="coerce")
    elif g["pe"].notna().sum() >= 30:
        g["pe_percentile"] = g["pe"].rolling(120, min_periods=30).apply(
            lambda s: (s.rank().iloc[-1] / len(s)) if len(s) > 0 else 0.5,
            raw=False,
        )
    else:
        g["pe_percentile"] = 0.5

    if "pb_percentile" in g.columns:
        g["pb_percentile"] = pd.to_numeric(g["pb_percentile"], errors="coerce")
    elif g["pb"].notna().sum() >= 30:
        g["pb_percentile"] = g["pb"].rolling(120, min_periods=30).apply(
            lambda s: (s.rank().iloc[-1] / len(s)) if len(s) > 0 else 0.5,
            raw=False,
        )
    else:
        g["pb_percentile"] = 0.5

    if "amplitude" in g.columns:
        g["amplitude"] = pd.to_numeric(g["amplitude"], errors="coerce")
    elif "high" in g.columns and "low" in g.columns:
        pre = pd.to_numeric(g.get("pre_close", g["close"].shift(1)), errors="coerce")
        g["amplitude"] = ((g["high"] - g["low"]) / pre.replace(0, np.nan) * 100).fillna(0)
    else:
        g["amplitude"] = g["return"].abs().fillna(0) * 100

    if g["turnover_rate"].isna().all():
        vol_ma = g["vol"].rolling(20, min_periods=1).mean()
        g["turnover_rate"] = (g["vol"] / vol_ma.replace(0, np.nan)).fillna(1.0)

    g["forward_return"] = g["close"].shift(-forward_days) / g["close"] - 1
    g = g.dropna(subset=["volatility", "forward_return"])
    g = g.replace([np.inf, -np.inf], np.nan).dropna(subset=["volatility", "volume_change_rate", "amplitude"])

    if len(g) < 50:
        return pd.DataFrame()

    q33, q67 = g["forward_return"].quantile([0.33, 0.67])
    g["risk_label"] = 1
    g.loc[g["forward_return"] <= q33, "risk_label"] = 2
    g.loc[g["forward_return"] >= q67, "risk_label"] = 0

    g["turnover_rate"] = g["turnover_rate"].fillna(g["turnover_rate"].median())
    g["pe_percentile"] = g["pe_percentile"].fillna(0.5)
    g["pb_percentile"] = g["pb_percentile"].fillna(0.5)
    g["amplitude"] = g["amplitude"].fillna(g["amplitude"].median())
    return g


def _evaluate_bundle(model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))
    recall_macro = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    report_dict = classification_report(
        y_test, y_pred, target_names=LABEL_NAMES, output_dict=True, zero_division=0,
    )
    return {
        "accuracy": acc,
        "recall_macro": recall_macro,
        "f1_macro": f1_macro,
        "report_dict": report_dict,
    }


def _evaluate_v1_baseline(stock_limit: int, years: int) -> dict | None:
    if not RF_MODEL_PATH.exists():
        return None
    try:
        bundle = joblib.load(RF_MODEL_PATH)
        model = bundle["model"]
        df = prepare_training_data(stock_limit=stock_limit, years=years, feature_version="v1")
        frames = []
        for _, group in df.groupby("ts_code"):
            feat = engineer_features(group)
            if not feat.empty:
                frames.append(feat)
        if not frames:
            return None
        data = pd.concat(frames, ignore_index=True)
        X = data[RF_V1_FEATURE_NAMES].astype(float).values
        y = data["risk_label"].astype(int).values
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        metrics = _evaluate_bundle(model, X_test, y_test)
        metrics["features"] = RF_V1_FEATURE_NAMES
        return metrics
    except Exception as exc:
        print(f"[RF v2] 基线评估跳过: {exc}")
        return None


def train_rf_v2(
    stock_limit: int = STOCK_LIMIT,
    years: int = TRAIN_YEARS_V2,
    force_refresh: bool = False,
) -> dict:
    df = prepare_training_data(
        stock_limit=stock_limit, years=years, force_refresh=force_refresh, feature_version="v2",
    )
    frames = []
    for _, group in df.groupby("ts_code"):
        feat = engineer_features_v2(group)
        if not feat.empty:
            frames.append(feat)

    if not frames:
        raise RuntimeError("v2 特征工程后无有效样本")

    data = pd.concat(frames, ignore_index=True)
    X = data[RF_V2_FEATURE_NAMES].astype(float).values
    y = data["risk_label"].astype(int).values
    print(f"[RF v2] 总样本数: {len(X)}, 标签分布: {pd.Series(y).value_counts().to_dict()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=RF_N_ESTIMATORS,
        max_depth=12,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    joblib.dump(
        {
            "model": model,
            "feature_names": RF_V2_FEATURE_NAMES,
            "label_names": LABEL_NAMES,
            "version": "v2.0",
        },
        RF_V2_MODEL_PATH,
    )

    importances = model.feature_importances_
    plt.figure(figsize=(8, 4))
    plt.bar(RF_V2_FEATURE_NAMES, importances, color="#6366f1")
    plt.title("Random Forest v2.0 Feature Importance")
    plt.ylabel("Importance")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(RF_V2_IMPORTANCE_PLOT, dpi=120)
    plt.close()

    eval_metrics = _evaluate_bundle(model, X_test, y_test)
    baseline = _evaluate_v1_baseline(stock_limit, years)

    metrics = {
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "train_accuracy": float(model.score(X_train, y_train)),
        "test_accuracy": eval_metrics["accuracy"],
        "recall_macro": eval_metrics["recall_macro"],
        "f1_macro": eval_metrics["f1_macro"],
        "feature_importance": {n: float(v) for n, v in zip(RF_V2_FEATURE_NAMES, importances)},
        "model_path": str(RF_V2_MODEL_PATH),
        "features": RF_V2_FEATURE_NAMES,
        "years": years,
        "data_source": "AKShare估值(优先) + Tushare日线",
    }

    meta_path = RF_V2_MODEL_PATH.with_suffix(".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    lines = [
        "# 随机森林 v2.0 风险评级模型评估报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 模型信息",
        f"- 模型路径: `{RF_V2_MODEL_PATH}`",
        f"- 特征: {', '.join(RF_V2_FEATURE_NAMES)}",
        f"- 训练区间: 近 {years} 年",
        f"- 测试样本: {len(X_test)}",
        "",
        "## 整体指标",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| 准确率 | {eval_metrics['accuracy']:.4f} |",
        f"| 召回率 (macro) | {eval_metrics['recall_macro']:.4f} |",
        f"| F1 (macro) | {eval_metrics['f1_macro']:.4f} |",
        "",
        "## 各类别指标",
        "| 类别 | Precision | Recall | F1 |",
        "|------|-----------|--------|-----|",
    ]
    for name in LABEL_NAMES:
        if name in eval_metrics["report_dict"]:
            r = eval_metrics["report_dict"][name]
            lines.append(f"| {name} | {r['precision']:.4f} | {r['recall']:.4f} | {r['f1-score']:.4f} |")

    RF_V2_EVAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    RF_V2_EVAL_REPORT.write_text("\n".join(lines), encoding="utf-8")

    compare_lines = [
        "# RF v1 vs v2 对比",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| 版本 | 特征数 | 准确率 | 召回率(macro) | F1(macro) |",
        "|------|--------|--------|---------------|-----------|",
        f"| v2.0 | {len(RF_V2_FEATURE_NAMES)} | {eval_metrics['accuracy']:.4f} | {eval_metrics['recall_macro']:.4f} | {eval_metrics['f1_macro']:.4f} |",
    ]
    if baseline:
        compare_lines.append(
            f"| v1 | {len(baseline['features'])} | {baseline['accuracy']:.4f} | {baseline['recall_macro']:.4f} | {baseline['f1_macro']:.4f} |"
        )
    RF_V2_COMPARE_REPORT.write_text("\n".join(compare_lines), encoding="utf-8")

    print(f"[RF v2] 模型已保存: {RF_V2_MODEL_PATH}")
    print(f"[RF v2] Accuracy={eval_metrics['accuracy']:.4f}, Recall={eval_metrics['recall_macro']:.4f}, F1={eval_metrics['f1_macro']:.4f}")
    print(f"[RF v2] 报告: {RF_V2_EVAL_REPORT}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="训练 RF v2.0")
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS_V2)
    parser.add_argument("--refresh", action="store_true", help="强制重新拉取数据")
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    train_rf_v2(stock_limit=limit, years=args.years, force_refresh=args.refresh)


if __name__ == "__main__":
    main()
