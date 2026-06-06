"""LSTM 模型评估：RMSE / MAE + evaluation_lstm.md"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from training.config import (
    LSTM_EVAL_REPORT,
    LSTM_MODEL_PATH,
    LSTM_PRED_LEN,
    LSTM_SCALER_PATH,
    LSTM_SEQ_LEN,
    STOCK_LIMIT,
    TRAIN_YEARS,
)
from training.data_fetch import prepare_training_data
from training.train_lstm import build_sequences


def evaluate_lstm(stock_limit: int = STOCK_LIMIT, years: int = TRAIN_YEARS) -> dict:
    if not LSTM_MODEL_PATH.exists():
        raise FileNotFoundError(f"未找到模型 {LSTM_MODEL_PATH}，请先运行 train_lstm.py")

    model = load_model(LSTM_MODEL_PATH, compile=False)
    scaler: MinMaxScaler = joblib.load(LSTM_SCALER_PATH)

    df = prepare_training_data(stock_limit=stock_limit, years=years)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])

    x_all, y_all = [], []
    for _, group in df.groupby("ts_code"):
        closes = group["close"].astype(float).values
        if len(closes) < LSTM_SEQ_LEN + LSTM_PRED_LEN + 10:
            continue
        x, y = build_sequences(closes, LSTM_SEQ_LEN, LSTM_PRED_LEN)
        if len(x):
            x_all.append(x)
            y_all.append(y)

    X = np.concatenate(x_all, axis=0)
    Y = np.concatenate(y_all, axis=0)
    X_scaled = scaler.transform(X.reshape(-1, 1)).reshape(X.shape[0], LSTM_SEQ_LEN, 1)
    Y_scaled = scaler.transform(Y.reshape(-1, 1)).reshape(Y.shape)

    _, X_test, _, y_test = train_test_split(X_scaled, Y_scaled, test_size=0.2, random_state=42)
    pred_scaled = model.predict(X_test, verbose=0)

    # 反归一化
    y_true = scaler.inverse_transform(y_test.reshape(-1, 1)).reshape(y_test.shape)
    y_pred = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).reshape(pred_scaled.shape)

    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))

    report = f"""# LSTM 周期预测模型评估报告

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 模型信息
- 模型路径: `{LSTM_MODEL_PATH}`
- 输入窗口: {LSTM_SEQ_LEN} 天
- 预测步长: {LSTM_PRED_LEN} 天
- 测试样本: {len(X_test)}

## 评估指标
| 指标 | 值 |
|------|-----|
| RMSE | {rmse:.4f} |
| MAE  | {mae:.4f} |

## 说明
- RMSE/MAE 基于反归一化后的收盘价（元）计算
- 测试集为随机 20%  hold-out，random_state=42
"""
    LSTM_EVAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    LSTM_EVAL_REPORT.write_text(report, encoding="utf-8")
    print(f"[评估] RMSE={rmse:.4f}, MAE={mae:.4f}")
    print(f"[评估] 报告: {LSTM_EVAL_REPORT}")
    return {"rmse": rmse, "mae": mae, "report": str(LSTM_EVAL_REPORT)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS)
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    evaluate_lstm(stock_limit=limit, years=args.years)


if __name__ == "__main__":
    main()
