"""
LSTM 周期预测模型训练
- 输入特征：收盘价、涨跌幅、成交量、PE 分位、PB 分位
- 滑窗：过去 30 天 -> 未来 5 天收盘价
- LSTM(64) -> Dropout(0.2) -> LSTM(32) -> Dense(5)
"""
import argparse
import json
import shutil
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
    LSTM_BASELINE_MODEL_PATH,
    LSTM_BASELINE_SCALER_PATH,
    LSTM_BATCH_SIZE,
    LSTM_EPOCHS,
    LSTM_FEATURE_NAMES,
    LSTM_LOSS_PLOT,
    LSTM_MODEL_PATH,
    LSTM_N_FEATURES,
    LSTM_PRED_LEN,
    LSTM_SCALER_PATH,
    LSTM_SEQ_LEN,
    PERCENTILE_WINDOW,
    STOCK_LIMIT,
    TRAIN_YEARS,
)
from training.data_fetch import prepare_training_data
from training.feature_engineering import build_feature_matrix


def build_sequences(features: np.ndarray, seq_len: int, pred_len: int):
    """features: (T, n_features)，close 在第 0 列"""
    x_list, y_list = [], []
    close_idx = LSTM_FEATURE_NAMES.index("close")
    for i in range(seq_len, len(features) - pred_len + 1):
        x_list.append(features[i - seq_len:i])
        y_list.append(features[i:i + pred_len, close_idx])
    return np.array(x_list), np.array(y_list)


def build_model(seq_len: int, pred_len: int, n_features: int) -> Sequential:
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(seq_len, n_features)),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dropout(0.2),
        Dense(pred_len),
    ])
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def _backup_baseline_if_needed() -> None:
    if LSTM_MODEL_PATH.exists() and not LSTM_BASELINE_MODEL_PATH.exists():
        shutil.copy2(LSTM_MODEL_PATH, LSTM_BASELINE_MODEL_PATH)
        print(f"[LSTM] 已备份基线模型 -> {LSTM_BASELINE_MODEL_PATH}")
    if LSTM_SCALER_PATH.exists() and not LSTM_BASELINE_SCALER_PATH.exists():
        shutil.copy2(LSTM_SCALER_PATH, LSTM_BASELINE_SCALER_PATH)
        print(f"[LSTM] 已备份基线 Scaler -> {LSTM_BASELINE_SCALER_PATH}")


def train_lstm(
    stock_limit: int = STOCK_LIMIT,
    years: int = TRAIN_YEARS,
    epochs: int = LSTM_EPOCHS,
) -> dict:
    df = prepare_training_data(stock_limit=stock_limit, years=years, force_refresh=False)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])

    x_all, y_all = [], []
    min_len = LSTM_SEQ_LEN + LSTM_PRED_LEN + PERCENTILE_WINDOW // 2
    for _, group in df.groupby("ts_code"):
        if len(group) < min_len:
            continue
        try:
            matrix = build_feature_matrix(group)
        except ValueError as e:
            print(f"[LSTM] 跳过 {group['ts_code'].iloc[0]}: {e}")
            continue
        x, y = build_sequences(matrix, LSTM_SEQ_LEN, LSTM_PRED_LEN)
        if len(x) == 0:
            continue
        x_all.append(x)
        y_all.append(y)

    if not x_all:
        raise RuntimeError("序列样本不足，请增加股票数量、历史区间或检查 PE/PB 数据")

    X = np.concatenate(x_all, axis=0)
    Y = np.concatenate(y_all, axis=0)
    print(f"[LSTM] 总样本数: {len(X)}，特征: {LSTM_FEATURE_NAMES}")

    feature_scaler = MinMaxScaler()
    target_scaler = MinMaxScaler()

    n_samples, seq_len, n_features = X.shape
    X_scaled = feature_scaler.fit_transform(X.reshape(-1, n_features)).reshape(n_samples, seq_len, n_features)
    Y_scaled = target_scaler.fit_transform(Y.reshape(-1, 1)).reshape(Y.shape)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, Y_scaled, test_size=0.2, random_state=42
    )

    _backup_baseline_if_needed()

    model = build_model(LSTM_SEQ_LEN, LSTM_PRED_LEN, LSTM_N_FEATURES)
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
    scaler_bundle = {
        "feature_scaler": feature_scaler,
        "target_scaler": target_scaler,
        "feature_names": LSTM_FEATURE_NAMES,
        "n_features": LSTM_N_FEATURES,
        "version": "v2_multifeature",
    }
    joblib.dump(scaler_bundle, LSTM_SCALER_PATH)

    plt.figure(figsize=(8, 5))
    plt.plot(history.history["loss"], label="train_loss")
    plt.plot(history.history["val_loss"], label="val_loss")
    plt.title("LSTM Training Loss (multi-feature)")
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
        "features": LSTM_FEATURE_NAMES,
        "percentile_window": PERCENTILE_WINDOW,
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
    parser.add_argument("--refresh", action="store_true", help="强制重新拉取 Tushare 数据")
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    if args.refresh:
        prepare_training_data(stock_limit=limit, years=args.years, force_refresh=True)
    train_lstm(stock_limit=limit, years=args.years, epochs=args.epochs)


if __name__ == "__main__":
    main()
