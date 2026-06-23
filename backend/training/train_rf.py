"""
随机森林风险评级模型训练（v2.2）
- v2.1 基础特征 + 交互特征（PE×波动率、PB×换手率、振幅×成交量变化率）
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
    RF_EVAL_REPORT,
    RF_FEATURE_NAMES,
    RF_FORWARD_DAYS,
    RF_IMPORTANCE_PLOT,
    RF_MODEL_PATH,
    RF_N_ESTIMATORS,
    STOCK_LIMIT,
    TRAIN_YEARS_V2,
)
from training.data_fetch import prepare_training_data
from training.feature_engineering import add_rf_interaction_features, add_technical_indicators

LABEL_NAMES = ["低风险", "中风险", "高风险"]
RF_V22_FEATURE_NAMES = RF_FEATURE_NAMES + [
    "pe_vol_interaction",
    "pb_turnover_interaction",
    "amp_volchg_interaction",
]


def engineer_features(group: pd.DataFrame, forward_days: int = RF_FORWARD_DAYS) -> pd.DataFrame:
    """v2.2 随机森林特征工程（含交互特征）"""
    g = add_technical_indicators(group.sort_values("trade_date").copy())
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
    g = g.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["volatility", "volume_change_rate", "amplitude", *RF_FEATURE_NAMES[6:]]
    )

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
    g["rsi_14"] = g["rsi_14"].fillna(50.0)
    g["ma5_bias"] = g["ma5_bias"].fillna(0.0)
    g["ma20_bias"] = g["ma20_bias"].fillna(0.0)
    g["bollinger_width"] = g["bollinger_width"].fillna(0.0)
    g["vol_ma5_ratio"] = g["vol_ma5_ratio"].fillna(1.0)
    g = add_rf_interaction_features(g)
    for col in RF_V22_FEATURE_NAMES[-3:]:
        g[col] = g[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return g.dropna(subset=RF_V22_FEATURE_NAMES)


def train_rf(
    stock_limit: int = STOCK_LIMIT,
    years: int = TRAIN_YEARS_V2,
    force_refresh: bool = False,
) -> dict:
    df = prepare_training_data(
        stock_limit=stock_limit, years=years, force_refresh=force_refresh, feature_version="v2",
    )
    frames = []
    for _, group in df.groupby("ts_code"):
        feat = engineer_features(group)
        if not feat.empty:
            frames.append(feat)

    if not frames:
        raise RuntimeError("特征工程后无有效样本")

    data = pd.concat(frames, ignore_index=True)
    X = data[RF_V22_FEATURE_NAMES].astype(float).values
    y = data["risk_label"].astype(int).values
    print(f"[RF v2.2] 总样本数: {len(X)}, 特征: {len(RF_V22_FEATURE_NAMES)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    joblib.dump(
        {
            "model": model,
            "feature_names": RF_V22_FEATURE_NAMES,
            "label_names": LABEL_NAMES,
            "version": "v2.2",
        },
        RF_MODEL_PATH,
    )

    importances = model.feature_importances_
    plt.figure(figsize=(10, 5))
    plt.bar(RF_V22_FEATURE_NAMES, importances, color="#6366f1")
    plt.title("Random Forest v2.2 Feature Importance")
    plt.ylabel("Importance")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(RF_IMPORTANCE_PLOT, dpi=120)
    plt.close()

    y_pred = model.predict(X_test)
    test_acc = float(accuracy_score(y_test, y_pred))
    recall_macro = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

    metrics = {
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "train_accuracy": float(model.score(X_train, y_train)),
        "test_accuracy": test_acc,
        "recall_macro": recall_macro,
        "f1_macro": f1_macro,
        "feature_importance": {n: float(v) for n, v in zip(RF_V22_FEATURE_NAMES, importances)},
        "model_path": str(RF_MODEL_PATH),
        "importance_plot": str(RF_IMPORTANCE_PLOT),
        "version": "v2.2",
    }

    meta_path = RF_MODEL_PATH.with_suffix(".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    report = f"""# 随机森林 v2.2 风险评级模型评估报告

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 整体指标
| 指标 | 值 |
|------|-----|
| 准确率 | {test_acc:.4f} |
| 召回率 (macro) | {recall_macro:.4f} |
| F1 (macro) | {f1_macro:.4f} |
"""
    RF_EVAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    RF_EVAL_REPORT.write_text(report, encoding="utf-8")

    print(f"[RF v2.2] 模型已保存: {RF_MODEL_PATH}")
    print(f"[RF v2.2] Accuracy={test_acc:.4f}, Recall={recall_macro:.4f}, F1={f1_macro:.4f}")

    try:
        from app.core import env_loader  # noqa: F401
        from app.services.model_manager import register_model_version
        version = register_model_version(
            "rf_risk", RF_MODEL_PATH, metrics,
            extra_files=[RF_IMPORTANCE_PLOT],
        )
        metrics["registered_version"] = version
    except Exception as e:
        print(f"[RF v2.2] 版本注册跳过: {e}")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="训练 RF v2.2")
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS_V2)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    train_rf(stock_limit=limit, years=args.years, force_refresh=args.refresh)


if __name__ == "__main__":
    main()
