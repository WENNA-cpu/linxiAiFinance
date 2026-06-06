"""
LSTM 周期预测模型训练
- MinMaxScaler 归一化
- 滑窗：过去 30 天 -> 未来 5 天收盘价
- LSTM(64) -> Dropout(0.2) -> LSTM(32) -> Dense(5)
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
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.models import Sequential

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from training.config import (
    LSTM_BATCH_SIZE,
    LSTM_EPOCHS,
    LSTM_LOSS_PLOT,
    LSTM_MODEL_PATH,
    LSTM_PRED_LEN,
    LSTM_SCALER_PATH,
    LSTM_SEQ_LEN,
    STOCK_LIMIT,
    TRAIN_YEARS,
)
from training.data_fetch import prepare_training_data


def build_sequences(close_values: np.ndarray, seq_len: int, pred_len: int):
    x_list, y_list = [], []
    for i in range(seq_len, len(close_values) - pred_len + 1):
        x_list.append(close_values[i - seq_len:i])
        y_list.append(close_values[i:i + pred_len])
    return np.array(x_list), np.array(y_list)


def build_model(seq_len: int, pred_len: int) -> Sequential:
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(seq_len, 1)),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dropout(0.2),
        Dense(pred_len),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def train_lstm(
    stock_limit: int = STOCK_LIMIT,
    years: int = TRAIN_YEARS,
    epochs: int = LSTM_EPOCHS,
) -> dict:
    df = prepare_training_data(stock_limit=stock_limit, years=years)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])

    x_all, y_all = [], []
    for _, group in df.groupby("ts_code"):
        closes = group["close"].astype(float).values
        if len(closes) < LSTM_SEQ_LEN + LSTM_PRED_LEN + 10:
            continue
        x, y = build_sequences(closes, LSTM_SEQ_LEN, LSTM_PRED_LEN)
        if len(x) == 0:
            continue
        x_all.append(x)
        y_all.append(y)

    if not x_all:
        raise RuntimeError("序列样本不足，请增加股票数量或历史区间")

    X = np.concatenate(x_all, axis=0)
    Y = np.concatenate(y_all, axis=0)
    print(f"[LSTM] 总样本数: {len(X)}")

    scaler = MinMaxScaler()
    flat = X.reshape(-1, 1)
    scaler.fit(flat)
    X_scaled = scaler.transform(X.reshape(-1, 1)).reshape(X.shape[0], LSTM_SEQ_LEN, 1)
    Y_scaled = scaler.transform(Y.reshape(-1, 1)).reshape(Y.shape)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, Y_scaled, test_size=0.2, random_state=42
    )

    model = build_model(LSTM_SEQ_LEN, LSTM_PRED_LEN)
    early_stop = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
    history = model.fit(
        X_train, y_train,
        validation_split=0.1,
        epochs=epochs,
        batch_size=LSTM_BATCH_SIZE,
        callbacks=[early_stop],
        verbose=1,
    )

    model.save(LSTM_MODEL_PATH)
    joblib.dump(scaler, LSTM_SCALER_PATH)

    # 损失曲线
    plt.figure(figsize=(8, 5))
    plt.plot(history.history["loss"], label="train_loss")
    plt.plot(history.history["val_loss"], label="val_loss")
    plt.title("LSTM Training Loss")
    plt.xlabel("Epoch")
    plt.ylabel("MSE")
    plt.legend()
    plt.tight_layout()
    plt.savefig(LSTM_LOSS_PLOT, dpi=120)
    plt.close()

    metrics = {
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "epochs_trained": len(history.history["loss"]),
        "final_loss": float(history.history["loss"][-1]),
        "final_val_loss": float(history.history["val_loss"][-1]),
        "model_path": str(LSTM_MODEL_PATH),
        "scaler_path": str(LSTM_SCALER_PATH),
        "loss_plot": str(LSTM_LOSS_PLOT),
    }

    meta_path = LSTM_MODEL_PATH.with_suffix(".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"[LSTM] 模型已保存: {LSTM_MODEL_PATH}")
    print(f"[LSTM] 损失曲线: {LSTM_LOSS_PLOT}")

    try:
        from app.core import env_loader  # noqa: F401
        from app.services.model_manager import register_model_version
        version = register_model_version(
            "lstm_cycle", LSTM_MODEL_PATH, metrics,
            extra_files=[LSTM_SCALER_PATH, LSTM_LOSS_PLOT],
        )
        metrics["version"] = version
        print(f"[LSTM] 已注册版本: {version}")
    except Exception as e:
        print(f"[LSTM] 版本注册跳过: {e}")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS)
    parser.add_argument("--epochs", type=int, default=LSTM_EPOCHS)
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    train_lstm(stock_limit=limit, years=args.years, epochs=args.epochs)


if __name__ == "__main__":
    main()
