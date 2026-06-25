"""
RF 冲刺训练：v2.1 + 交互特征 + 超参搜索
- 数据划分 70% / 15% / 15%（训练 / 验证 / 测试）
- 达标保存 v2.2(>=59%) 或 v2.1.1(58-59%)，否则保持 v2.1
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
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.model_selection import RandomizedSearchCV, train_test_split

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from training.config import (
    MODELS_DIR,
    REPORTS_DIR,
    RF_FEATURE_NAMES,
    RF_INTERACTION_FEATURE_NAMES,
    RF_MODEL_PATH,
    RF_SPRINT_FEATURE_NAMES,
    STOCK_LIMIT,
    TRAIN_YEARS_V2,
)
from training.data_fetch import prepare_training_data
from training.feature_engineering import add_rf_interaction_features
from training.train_rf import LABEL_NAMES, engineer_features

V21_BASELINE = 0.5691
THRESH_V22 = 0.59
THRESH_V211 = 0.58
THRESH_ABANDON = 0.575


def engineer_features_sprint(group: pd.DataFrame) -> pd.DataFrame:
    g = engineer_features(group)
    if g.empty:
        return g
    g = add_rf_interaction_features(g)
    for col in RF_INTERACTION_FEATURE_NAMES:
        g[col] = g[col].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return g.dropna(subset=RF_SPRINT_FEATURE_NAMES)


def split_70_15_15(X: np.ndarray, y: np.ndarray):
    X_train, X_tmp, y_train, y_tmp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y,
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_tmp, y_tmp, test_size=0.50, random_state=42, stratify=y_tmp,
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def tune_rf(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    param_dist = {
        "n_estimators": [100, 200, 300],
        "max_depth": [10, 15, 20],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
    }
    search = RandomizedSearchCV(
        RandomForestClassifier(random_state=42, n_jobs=-1),
        param_distributions=param_dist,
        n_iter=24,
        cv=3,
        scoring="accuracy",
        random_state=42,
        n_jobs=-1,
        verbose=1,
    )
    search.fit(X_train, y_train)
    print(f"[Sprint] 最优参数: {search.best_params_}")
    print(f"[Sprint] CV 准确率: {search.best_score_:.4f}")
    return search.best_estimator_


def evaluate(model, X, y) -> dict:
    pred = model.predict(X)
    return {
        "accuracy": float(accuracy_score(y, pred)),
        "recall": float(recall_score(y, pred, average="macro", zero_division=0)),
        "f1": float(f1_score(y, pred, average="macro", zero_division=0)),
    }


def feature_importance_ranking(model, feature_names: list[str]) -> list[tuple[str, float]]:
    pairs = list(zip(feature_names, model.feature_importances_))
    return sorted(pairs, key=lambda x: x[1], reverse=True)


def decide_version(test_acc: float) -> str | None:
    if test_acc >= THRESH_V22:
        return "v2.2"
    if test_acc >= THRESH_V211:
        return "v2.1.1"
    if test_acc < THRESH_ABANDON:
        return None
    return None


def save_model(
    model,
    version: str,
    feature_names: list[str],
    metrics: dict,
    importance_plot: Path,
) -> Path:
    version_path = MODELS_DIR / f"rf_risk_{version}.pkl"
    bundle = {
        "model": model,
        "feature_names": feature_names,
        "label_names": LABEL_NAMES,
        "version": version,
        "best_params": metrics.get("best_params"),
    }
    joblib.dump(bundle, version_path)
    if version in ("v2.2", "v2.1.1"):
        joblib.dump(bundle, RF_MODEL_PATH)

    ranked = feature_importance_ranking(model, feature_names)
    names, imps = zip(*ranked)
    plt.figure(figsize=(11, 5))
    plt.bar(names, imps, color="#6366f1")
    plt.title(f"Random Forest {version} Feature Importance")
    plt.ylabel("Importance")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(importance_plot, dpi=120)
    plt.close()

    meta = {
        "version": version,
        "features": feature_names,
        "interaction_features": RF_INTERACTION_FEATURE_NAMES,
        "best_params": metrics.get("best_params"),
        "created_at": datetime.now().isoformat(),
        **metrics,
    }
    meta_path = MODELS_DIR / f"rf_risk_{version}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return version_path


def run_sprint(stock_limit: int = STOCK_LIMIT, years: int = TRAIN_YEARS_V2) -> dict:
    limit = stock_limit if stock_limit > 0 else 300
    df = prepare_training_data(
        stock_limit=limit, years=years, force_refresh=False, feature_version="v2",
    )
    frames = []
    for _, group in df.groupby("ts_code"):
        feat = engineer_features_sprint(group)
        if not feat.empty:
            frames.append(feat)
    if not frames:
        raise RuntimeError("特征工程后无有效样本")

    data = pd.concat(frames, ignore_index=True)
    X = data[RF_SPRINT_FEATURE_NAMES].astype(float).values
    y = data["risk_label"].astype(int).values
    print(f"[Sprint] 样本数: {len(X)}, 特征数: {len(RF_SPRINT_FEATURE_NAMES)}")

    X_train, X_val, X_test, y_train, y_val, y_test = split_70_15_15(X, y)
    print(
        f"[Sprint] 划分 train={len(X_train)} val={len(X_val)} test={len(X_test)}"
    )

    model = tune_rf(X_train, y_train)
    best_params = model.get_params()
    train_m = evaluate(model, X_train, y_train)
    val_m = evaluate(model, X_val, y_val)
    test_m = evaluate(model, X_test, y_test)

    ranked = feature_importance_ranking(model, RF_SPRINT_FEATURE_NAMES)
    top5 = ranked[:5]
    interaction_in_top5 = [
        name for name, _ in top5 if name in RF_INTERACTION_FEATURE_NAMES
    ]

    print("\n=== 评估结果（测试集） ===")
    print(f"准确率: {test_m['accuracy']:.4f} ({test_m['accuracy']*100:.2f}%)")
    print(f"召回率: {test_m['recall']:.4f}")
    print(f"F1:     {test_m['f1']:.4f}")
    print(f"\n验证集准确率: {val_m['accuracy']:.4f}")
    print(f"基线 v2.1: {V21_BASELINE:.4f}")

    print("\n=== 特征重要性 Top 5 ===")
    for i, (name, imp) in enumerate(top5, 1):
        tag = " [交互]" if name in RF_INTERACTION_FEATURE_NAMES else ""
        print(f"  {i}. {name}: {imp:.4f}{tag}")

    version = decide_version(test_m["accuracy"])
    result = {
        "train": train_m,
        "val": val_m,
        "test": test_m,
        "best_params": {
            k: best_params[k]
            for k in ("n_estimators", "max_depth", "min_samples_split", "min_samples_leaf")
        },
        "feature_importance_top5": [{"name": n, "importance": float(v)} for n, v in top5],
        "interaction_in_top5": interaction_in_top5,
        "saved_version": version,
    }

    if version:
        plot = REPORTS_DIR / f"rf_{version.replace('.', '')}_feature_importance.png"
        path = save_model(model, version, RF_SPRINT_FEATURE_NAMES, result, plot)
        print(f"\n[保存] {version} -> {path} (生产: {RF_MODEL_PATH})")
        try:
            from app.core import env_loader  # noqa: F401
            from app.services.model_manager import register_model_version
            reg = register_model_version(
                "rf_risk",
                RF_MODEL_PATH,
                {
                    "test_accuracy": test_m["accuracy"],
                    "recall_macro": test_m["recall"],
                    "f1_macro": test_m["f1"],
                    "features": RF_SPRINT_FEATURE_NAMES,
                    "version": version,
                },
                extra_files=[plot],
            )
            result["registered_version"] = reg
        except Exception as e:
            print(f"[Sprint] 版本注册跳过: {e}")
    else:
        if test_m["accuracy"] >= THRESH_ABANDON:
            print(
                f"\n[放弃] 测试准确率 {test_m['accuracy']:.4f} 在 57.5%-58% 之间，"
                "未达 v2.1.1 门槛，保持 v2.1"
            )
        else:
            print(f"\n[放弃] 测试准确率 {test_m['accuracy']:.4f} < 57.5%，保持 v2.1")

    report = REPORTS_DIR / "evaluation_rf_sprint.md"
    lines = [
        f"# RF 冲刺评估 ({datetime.now():%Y-%m-%d %H:%M:%S})",
        "",
        "## 测试集",
        f"- 准确率: {test_m['accuracy']:.4f}",
        f"- 召回率: {test_m['recall']:.4f}",
        f"- F1: {test_m['f1']:.4f}",
        "",
        "## Top 5 特征",
    ]
    for i, (n, v) in enumerate(top5, 1):
        lines.append(f"{i}. {n}: {v:.4f}")
    lines.append(f"\n交互特征进入 Top5: {interaction_in_top5 or '无'}")
    lines.append(f"\n结论: {version or '保持 v2.1'}")
    report.write_text("\n".join(lines), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="RF 冲刺 60%")
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS_V2)
    args = parser.parse_args()
    run_sprint(stock_limit=args.limit, years=args.years)


if __name__ == "__main__":
    main()
