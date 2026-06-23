"""随机森林模型评估：准确率 / 召回率 / F1 + evaluation_rf.md"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from training.config import RF_EVAL_REPORT, RF_FEATURE_NAMES, RF_MODEL_PATH, STOCK_LIMIT, TRAIN_YEARS_V2
from training.data_fetch import prepare_training_data
from training.train_rf import LABEL_NAMES, engineer_features


def evaluate_rf(stock_limit: int = STOCK_LIMIT, years: int = TRAIN_YEARS_V2) -> dict:
    if not RF_MODEL_PATH.exists():
        raise FileNotFoundError(f"未找到模型 {RF_MODEL_PATH}，请先运行 train_rf.py")

    bundle = joblib.load(RF_MODEL_PATH)
    model = bundle["model"]

    df = prepare_training_data(stock_limit=stock_limit, years=years)
    frames = []
    for _, group in df.groupby("ts_code"):
        feat = engineer_features(group)
        if not feat.empty:
            frames.append(feat)
    data = pd.concat(frames, ignore_index=True)
    X = data[RF_FEATURE_NAMES].astype(float).values
    y = data["risk_label"].astype(int).values

    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    y_pred = model.predict(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    f1_macro = float(f1_score(y_test, y_pred, average="macro"))
    f1_weighted = float(f1_score(y_test, y_pred, average="weighted"))
    report_dict = classification_report(
        y_test, y_pred, target_names=LABEL_NAMES, output_dict=True, zero_division=0
    )

    lines = [
        "# 随机森林风险评级模型评估报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 模型信息",
        f"- 模型路径: `{RF_MODEL_PATH}`",
        f"- 特征: {', '.join(RF_FEATURE_NAMES)}",
        f"- 测试样本: {len(X_test)}",
        "",
        "## 整体指标",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| 准确率 | {acc:.4f} |",
        f"| F1 (macro) | {f1_macro:.4f} |",
        f"| F1 (weighted) | {f1_weighted:.4f} |",
        "",
        "## 各类别指标",
        "| 类别 | Precision | Recall | F1 |",
        "|------|-----------|--------|-----|",
    ]
    for name in LABEL_NAMES:
        if name in report_dict:
            r = report_dict[name]
            lines.append(f"| {name} | {r['precision']:.4f} | {r['recall']:.4f} | {r['f1-score']:.4f} |")

    RF_EVAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    RF_EVAL_REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"[评估] Accuracy={acc:.4f}, F1(macro)={f1_macro:.4f}")
    print(f"[评估] 报告: {RF_EVAL_REPORT}")
    return {"accuracy": acc, "f1_macro": f1_macro, "report": str(RF_EVAL_REPORT)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS)
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    evaluate_rf(stock_limit=limit, years=args.years)


if __name__ == "__main__":
    main()
