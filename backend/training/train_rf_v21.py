"""
随机森林 v2.1 训练 — v2.0 特征 + 技术指标（RSI、均线乖离、布林带、量比）
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
    RF_N_ESTIMATORS,
    RF_V21_COMPARE_REPORT,
    RF_V21_EVAL_REPORT,
    RF_V21_FEATURE_NAMES,
    RF_V21_IMPORTANCE_PLOT,
    RF_V21_MODEL_PATH,
    RF_V2_FEATURE_NAMES,
    RF_V2_MODEL_PATH,
    STOCK_LIMIT,
    TRAIN_YEARS_V2,
)
from training.data_fetch import prepare_training_data
from training.feature_engineering import add_technical_indicators
from training.train_rf import LABEL_NAMES
from training.train_rf_v2 import _evaluate_bundle, engineer_features_v2


def engineer_features_v21(group: pd.DataFrame, forward_days: int = RF_FORWARD_DAYS) -> pd.DataFrame:
    """v2.1：在 v2 特征基础上叠加技术指标"""
    g = add_technical_indicators(group)
    g = engineer_features_v2(g, forward_days=forward_days)
    if g.empty:
        return g

    for col in ("rsi_14", "ma5_bias", "ma20_bias", "bollinger_width", "vol_ma5_ratio"):
        if col not in g.columns:
            return pd.DataFrame()
        g[col] = pd.to_numeric(g[col], errors="coerce")

    g = g.dropna(subset=["rsi_14", "ma5_bias", "ma20_bias", "bollinger_width", "vol_ma5_ratio"])
    g["rsi_14"] = g["rsi_14"].fillna(50.0)
    g["ma5_bias"] = g["ma5_bias"].fillna(0.0)
    g["ma20_bias"] = g["ma20_bias"].fillna(0.0)
    g["bollinger_width"] = g["bollinger_width"].fillna(0.0)
    g["vol_ma5_ratio"] = g["vol_ma5_ratio"].fillna(1.0)
    return g


def _evaluate_v2_baseline(stock_limit: int, years: int) -> dict | None:
    if not RF_V2_MODEL_PATH.exists():
        return None
    try:
        bundle = joblib.load(RF_V2_MODEL_PATH)
        model = bundle["model"]
        df = prepare_training_data(stock_limit=stock_limit, years=years, feature_version="v2")
        frames = []
        for _, group in df.groupby("ts_code"):
            feat = engineer_features_v2(group)
            if not feat.empty:
                frames.append(feat)
        if not frames:
            return None
        data = pd.concat(frames, ignore_index=True)
        X = data[RF_V2_FEATURE_NAMES].astype(float).values
        y = data["risk_label"].astype(int).values
        _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        metrics = _evaluate_bundle(model, X_test, y_test)
        metrics["features"] = RF_V2_FEATURE_NAMES
        return metrics
    except Exception as exc:
        print(f"[RF v2.1] v2.0 基线评估跳过: {exc}")
        return None


def train_rf_v21(
    stock_limit: int = STOCK_LIMIT,
    years: int = TRAIN_YEARS_V2,
    force_refresh: bool = False,
) -> dict:
    df = prepare_training_data(
        stock_limit=stock_limit, years=years, force_refresh=force_refresh, feature_version="v2",
    )
    frames = []
    for _, group in df.groupby("ts_code"):
        feat = engineer_features_v21(group)
        if not feat.empty:
            frames.append(feat)

    if not frames:
        raise RuntimeError("v2.1 特征工程后无有效样本")

    data = pd.concat(frames, ignore_index=True)
    X = data[RF_V21_FEATURE_NAMES].astype(float).values
    y = data["risk_label"].astype(int).values
    print(f"[RF v2.1] 总样本数: {len(X)}, 特征数: {len(RF_V21_FEATURE_NAMES)}")
    print(f"[RF v2.1] 标签分布: {pd.Series(y).value_counts().to_dict()}")

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
            "feature_names": RF_V21_FEATURE_NAMES,
            "label_names": LABEL_NAMES,
            "version": "v2.1",
        },
        RF_V21_MODEL_PATH,
    )

    importances = model.feature_importances_
    plt.figure(figsize=(10, 5))
    plt.bar(RF_V21_FEATURE_NAMES, importances, color="#6366f1")
    plt.title("Random Forest v2.1 Feature Importance")
    plt.ylabel("Importance")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(RF_V21_IMPORTANCE_PLOT, dpi=120)
    plt.close()

    eval_metrics = _evaluate_bundle(model, X_test, y_test)
    baseline_v2 = _evaluate_v2_baseline(stock_limit, years)

    metrics = {
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "train_accuracy": float(model.score(X_train, y_train)),
        "test_accuracy": eval_metrics["accuracy"],
        "recall_macro": eval_metrics["recall_macro"],
        "f1_macro": eval_metrics["f1_macro"],
        "feature_importance": {n: float(v) for n, v in zip(RF_V21_FEATURE_NAMES, importances)},
        "model_path": str(RF_V21_MODEL_PATH),
        "features": RF_V21_FEATURE_NAMES,
        "years": years,
    }

    meta_path = RF_V21_MODEL_PATH.with_suffix(".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    lines = [
        "# 随机森林 v2.1 风险评级模型评估报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 模型信息",
        f"- 模型路径: `{RF_V21_MODEL_PATH}`",
        f"- 特征 ({len(RF_V21_FEATURE_NAMES)}): {', '.join(RF_V21_FEATURE_NAMES)}",
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
        "## 新增技术指标",
        "- RSI(14)、MA5/MA20 乖离率、布林带宽度、成交量 MA5 比值",
        "",
        "## 各类别指标",
        "| 类别 | Precision | Recall | F1 |",
        "|------|-----------|--------|-----|",
    ]
    for name in LABEL_NAMES:
        if name in eval_metrics["report_dict"]:
            r = eval_metrics["report_dict"][name]
            lines.append(f"| {name} | {r['precision']:.4f} | {r['recall']:.4f} | {r['f1-score']:.4f} |")

    RF_V21_EVAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    RF_V21_EVAL_REPORT.write_text("\n".join(lines), encoding="utf-8")

    compare_lines = [
        "# RF v2.0 vs v2.1 对比",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| 版本 | 特征数 | 准确率 | 召回率(macro) | F1(macro) |",
        "|------|--------|--------|---------------|-----------|",
        f"| v2.1 | {len(RF_V21_FEATURE_NAMES)} | {eval_metrics['accuracy']:.4f} | {eval_metrics['recall_macro']:.4f} | {eval_metrics['f1_macro']:.4f} |",
    ]
    if baseline_v2:
        compare_lines.append(
            f"| v2.0 | {len(baseline_v2['features'])} | {baseline_v2['accuracy']:.4f} | "
            f"{baseline_v2['recall_macro']:.4f} | {baseline_v2['f1_macro']:.4f} |"
        )
        acc_delta = eval_metrics["accuracy"] - baseline_v2["accuracy"]
        f1_delta = eval_metrics["f1_macro"] - baseline_v2["f1_macro"]
        compare_lines.extend([
            "",
            "## 变化",
            f"- 准确率: {'+' if acc_delta >= 0 else ''}{acc_delta * 100:.2f}%",
            f"- F1(macro): {'+' if f1_delta >= 0 else ''}{f1_delta * 100:.2f}%",
        ])
    RF_V21_COMPARE_REPORT.write_text("\n".join(compare_lines), encoding="utf-8")

    print(f"[RF v2.1] 模型已保存: {RF_V21_MODEL_PATH}")
    print(
        f"[RF v2.1] Accuracy={eval_metrics['accuracy']:.4f}, "
        f"Recall={eval_metrics['recall_macro']:.4f}, F1={eval_metrics['f1_macro']:.4f}"
    )
    if baseline_v2:
        print(
            f"[RF v2.1] vs v2.0: Acc {eval_metrics['accuracy'] - baseline_v2['accuracy']:+.4f}, "
            f"F1 {eval_metrics['f1_macro'] - baseline_v2['f1_macro']:+.4f}"
        )
    print(f"[RF v2.1] 报告: {RF_V21_EVAL_REPORT}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="训练 RF v2.1（技术指标增强）")
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS_V2)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    train_rf_v21(stock_limit=limit, years=args.years, force_refresh=args.refresh)


if __name__ == "__main__":
    main()
