"""
随机森林风险评级模型训练
- 特征：波动率、换手率、估值分位、成交量变化率
- 标签：低/中/高（基于未来收益率分位数）
"""
import argparse
import json
import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from training.config import (
    RF_FORWARD_DAYS,
    RF_IMPORTANCE_PLOT,
    RF_MODEL_PATH,
    RF_N_ESTIMATORS,
    STOCK_LIMIT,
    TRAIN_YEARS,
)
from training.data_fetch import prepare_training_data

FEATURE_NAMES = ["volatility", "turnover_rate", "pe_percentile", "volume_change_rate"]
LABEL_NAMES = ["低风险", "中风险", "高风险"]


def engineer_features(group: pd.DataFrame, forward_days: int = RF_FORWARD_DAYS) -> pd.DataFrame:
    g = group.sort_values("trade_date").copy()
    g["close"] = pd.to_numeric(g["close"], errors="coerce")
    g["vol"] = pd.to_numeric(g["vol"], errors="coerce")
    g["pe"] = pd.to_numeric(g.get("pe"), errors="coerce")
    g["turnover_rate"] = pd.to_numeric(g.get("turnover_rate"), errors="coerce")

    g["return"] = g["close"].pct_change()
    g["volatility"] = g["return"].rolling(20).std()
    g["volume_change_rate"] = g["vol"].pct_change()
    if "pe" in g.columns and g["pe"].notna().sum() >= 30:
        g["pe_percentile"] = g["pe"].rolling(120, min_periods=30).apply(
            lambda s: (s.rank().iloc[-1] / len(s)) if len(s) > 0 else 0.5,
            raw=False,
        )
    else:
        g["pe_percentile"] = g["close"].rolling(120, min_periods=30).apply(
            lambda s: (s.rank().iloc[-1] / len(s)) if len(s) > 0 else 0.5,
            raw=False,
        )
    if "turnover_rate" not in g.columns or g["turnover_rate"].isna().all():
        vol_ma = g["vol"].rolling(20).mean()
        g["turnover_rate"] = (g["vol"] / vol_ma.replace(0, np.nan)).fillna(1.0)
    g["forward_return"] = g["close"].shift(-forward_days) / g["close"] - 1

    g = g.dropna(subset=["volatility", "forward_return"])
    g = g.replace([np.inf, -np.inf], np.nan).dropna(subset=["volatility", "volume_change_rate"])

    if len(g) < 50:
        return pd.DataFrame()

    # 标签：按未来收益分位数 -> 0低 1中 2高（收益越低风险越高，标签反转）
    q33, q67 = g["forward_return"].quantile([0.33, 0.67])
    g["risk_label"] = 1
    g.loc[g["forward_return"] <= q33, "risk_label"] = 2  # 低未来收益 -> 高风险
    g.loc[g["forward_return"] >= q67, "risk_label"] = 0  # 高未来收益 -> 低风险

    g["turnover_rate"] = g["turnover_rate"].fillna(g["turnover_rate"].median())
    g["pe_percentile"] = g["pe_percentile"].fillna(0.5)
    return g


def train_rf(stock_limit: int = STOCK_LIMIT, years: int = TRAIN_YEARS) -> dict:
    df = prepare_training_data(stock_limit=stock_limit, years=years)
    frames = []
    for code, group in df.groupby("ts_code"):
        feat = engineer_features(group)
        if not feat.empty:
            frames.append(feat)

    if not frames:
        raise RuntimeError("特征工程后无有效样本")

    data = pd.concat(frames, ignore_index=True)
    X = data[FEATURE_NAMES].astype(float).values
    y = data["risk_label"].astype(int).values
    print(f"[RF] 总样本数: {len(X)}, 标签分布: {pd.Series(y).value_counts().to_dict()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
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
            "feature_names": FEATURE_NAMES,
            "label_names": LABEL_NAMES,
        },
        RF_MODEL_PATH,
    )

    importances = model.feature_importances_
    plt.figure(figsize=(7, 4))
    plt.bar(FEATURE_NAMES, importances, color="#6366f1")
    plt.title("Random Forest Feature Importance")
    plt.ylabel("Importance")
    plt.tight_layout()
    plt.savefig(RF_IMPORTANCE_PLOT, dpi=120)
    plt.close()

    train_acc = float(model.score(X_train, y_train))
    test_acc = float(model.score(X_test, y_test))

    metrics = {
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "train_accuracy": train_acc,
        "test_accuracy": test_acc,
        "feature_importance": {n: float(v) for n, v in zip(FEATURE_NAMES, importances)},
        "model_path": str(RF_MODEL_PATH),
        "importance_plot": str(RF_IMPORTANCE_PLOT),
    }

    meta_path = RF_MODEL_PATH.with_suffix(".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"[RF] 模型已保存: {RF_MODEL_PATH}")
    print(f"[RF] 测试准确率: {test_acc:.4f}")

    try:
        from app.core import env_loader  # noqa: F401
        from app.services.model_manager import register_model_version
        version = register_model_version(
            "rf_risk", RF_MODEL_PATH, metrics,
            extra_files=[RF_IMPORTANCE_PLOT],
        )
        metrics["version"] = version
        print(f"[RF] 已注册版本: {version}")
    except Exception as e:
        print(f"[RF] 版本注册跳过: {e}")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS)
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    train_rf(stock_limit=limit, years=args.years)


if __name__ == "__main__":
    main()
