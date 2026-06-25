"""
LSTM v2.0 训练 — AKShare 估值 + 扩展特征
特征：收盘价、涨跌幅、成交量、PE分位、PB分位、换手率、振幅
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
from sklearn.metrics import mean_absolute_error, mean_squared_error
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
    LSTM_FEATURE_NAMES,
    LSTM_MODEL_PATH,
    LSTM_PRED_LEN,
    LSTM_SCALER_PATH,
    LSTM_SEQ_LEN,
    LSTM_V2_COMPARE_REPORT,
    LSTM_V2_EVAL_REPORT,
    LSTM_V2_FEATURE_NAMES,
    LSTM_V2_LOSS_PLOT,
    LSTM_V2_MODEL_PATH,
    LSTM_V2_N_FEATURES,
    LSTM_V2_SCALER_PATH,
    PERCENTILE_WINDOW,
    STOCK_LIMIT,
    TRAIN_YEARS_V2,
)
from training.data_fetch import prepare_training_data
from training.feature_engineering import build_feature_matrix, build_feature_matrix_v2


def build_sequences(features: np.ndarray, seq_len: int, pred_len: int, close_idx: int = 0):
    x_list, y_list = [], []
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


def _evaluate_model(model, feature_scaler, target_scaler, X_test, y_test, n_features: int) -> dict:
    if n_features > 1:
        ns, sl, nf = X_test.shape
        X_in = feature_scaler.transform(X_test.reshape(-1, nf)).reshape(ns, sl, nf)
    else:
        X_in = feature_scaler.transform(X_test.reshape(-1, 1)).reshape(X_test.shape[0], LSTM_SEQ_LEN, 1)

    y_in = target_scaler.transform(y_test.reshape(-1, 1)).reshape(y_test.shape)
    pred_scaled = model.predict(X_in, verbose=0)
    y_true = target_scaler.inverse_transform(y_in.reshape(-1, 1)).reshape(y_in.shape)
    y_pred = target_scaler.inverse_transform(pred_scaled.reshape(-1, 1)).reshape(pred_scaled.shape)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    return {"rmse": rmse, "mae": mae}


def _load_baseline_metrics(stock_limit: int, years: int) -> dict | None:
    if not LSTM_MODEL_PATH.exists() or not LSTM_SCALER_PATH.exists():
        return None
    try:
        from tensorflow.keras.models import load_model
        from training.evaluate_lstm import _load_scalers, _prepare_dataset

        model = load_model(LSTM_MODEL_PATH, compile=False)
        fs, ts, nf = _load_scalers(LSTM_SCALER_PATH)
        X, Y = _prepare_dataset(stock_limit, years, multi_feature=nf > 1)
        ns, sl, nfeat = X.shape if nf > 1 else (X.shape[0], LSTM_SEQ_LEN, 1)
        if nf > 1:
            Xs = fs.transform(X.reshape(-1, nfeat)).reshape(ns, sl, nfeat)
        else:
            Xs = fs.transform(X.reshape(-1, 1)).reshape(X.shape[0], LSTM_SEQ_LEN, 1)
        Ys = ts.transform(Y.reshape(-1, 1)).reshape(Y.shape)
        _, X_test, _, y_test = train_test_split(Xs, Ys, test_size=0.2, random_state=42)
        y_pred = model.predict(X_test, verbose=0)
        y_true = ts.inverse_transform(y_test.reshape(-1, 1)).reshape(y_test.shape)
        y_hat = ts.inverse_transform(y_pred.reshape(-1, 1)).reshape(y_pred.shape)
        return {
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_hat))),
            "mae": float(mean_absolute_error(y_true, y_hat)),
            "features": LSTM_FEATURE_NAMES,
        }
    except Exception as exc:
        print(f"[LSTM v2] 基线评估跳过: {exc}")
        return None


def train_lstm_v2(
    stock_limit: int = STOCK_LIMIT,
    years: int = TRAIN_YEARS_V2,
    epochs: int = LSTM_EPOCHS,
    force_refresh: bool = False,
) -> dict:
    df = prepare_training_data(
        stock_limit=stock_limit, years=years, force_refresh=force_refresh, feature_version="v2",
    )
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])

    close_idx = LSTM_V2_FEATURE_NAMES.index("close")
    min_len = LSTM_SEQ_LEN + LSTM_PRED_LEN + PERCENTILE_WINDOW // 2
    x_all, y_all = [], []
    for _, group in df.groupby("ts_code"):
        if len(group) < min_len:
            continue
        try:
            matrix = build_feature_matrix_v2(group)
        except ValueError as e:
            print(f"[LSTM v2] 跳过 {group['ts_code'].iloc[0]}: {e}")
            continue
        x, y = build_sequences(matrix, LSTM_SEQ_LEN, LSTM_PRED_LEN, close_idx=close_idx)
        if len(x):
            x_all.append(x)
            y_all.append(y)

    if not x_all:
        raise RuntimeError("v2 序列样本不足，请检查 AKShare 估值数据或增加股票数量")

    X = np.concatenate(x_all, axis=0)
    Y = np.concatenate(y_all, axis=0)
    print(f"[LSTM v2] 总样本数: {len(X)}，特征: {LSTM_V2_FEATURE_NAMES}")

    feature_scaler = MinMaxScaler()
    target_scaler = MinMaxScaler()
    n_samples, seq_len, n_features = X.shape
    X_scaled = feature_scaler.fit_transform(X.reshape(-1, n_features)).reshape(n_samples, seq_len, n_features)
    Y_scaled = target_scaler.fit_transform(Y.reshape(-1, 1)).reshape(Y.shape)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, Y_scaled, test_size=0.2, random_state=42,
    )

    model = build_model(LSTM_SEQ_LEN, LSTM_PRED_LEN, LSTM_V2_N_FEATURES)
    early_stop = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
    history = model.fit(
        X_train, y_train,
        validation_split=0.1,
        epochs=epochs,
        batch_size=LSTM_BATCH_SIZE,
        callbacks=[early_stop],
        verbose=1,
    )

    model.save(LSTM_V2_MODEL_PATH)
    joblib.dump(
        {
            "feature_scaler": feature_scaler,
            "target_scaler": target_scaler,
            "feature_names": LSTM_V2_FEATURE_NAMES,
            "n_features": LSTM_V2_N_FEATURES,
            "version": "v2.0",
        },
        LSTM_V2_SCALER_PATH,
    )

    plt.figure(figsize=(8, 5))
    plt.plot(history.history["loss"], label="train_loss")
    plt.plot(history.history["val_loss"], label="val_loss")
    plt.title("LSTM v2.0 Training Loss")
    plt.xlabel("Epoch")
    plt.ylabel("MSE")
    plt.legend()
    plt.tight_layout()
    plt.savefig(LSTM_V2_LOSS_PLOT, dpi=120)
    plt.close()

    eval_metrics = _evaluate_model(model, feature_scaler, target_scaler, X_test, y_test, LSTM_V2_N_FEATURES)
    baseline = _load_baseline_metrics(stock_limit, years)

    metrics = {
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "epochs_trained": len(history.history["loss"]),
        "final_loss": float(history.history["loss"][-1]),
        "final_val_loss": float(history.history["val_loss"][-1]),
        "rmse": eval_metrics["rmse"],
        "mae": eval_metrics["mae"],
        "model_path": str(LSTM_V2_MODEL_PATH),
        "scaler_path": str(LSTM_V2_SCALER_PATH),
        "features": LSTM_V2_FEATURE_NAMES,
        "years": years,
        "data_source": "AKShare估值(优先) + Tushare日线",
    }

    meta_path = LSTM_V2_MODEL_PATH.with_suffix(".meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    report_lines = [
        "# LSTM v2.0 周期预测模型评估报告",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 模型信息",
        f"- 模型路径: `{LSTM_V2_MODEL_PATH}`",
        f"- 输入窗口: {LSTM_SEQ_LEN} 天",
        f"- 预测步长: {LSTM_PRED_LEN} 天",
        f"- 输入特征: {LSTM_V2_FEATURE_NAMES}",
        f"- 训练区间: 近 {years} 年",
        f"- 测试样本: {len(X_test)}",
        "",
        "## 评估指标",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| RMSE | {eval_metrics['rmse']:.4f} |",
        f"| MAE  | {eval_metrics['mae']:.4f} |",
    ]
    LSTM_V2_EVAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    LSTM_V2_EVAL_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    compare_lines = [
        "# LSTM v1 vs v2 对比",
        "",
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| 版本 | 特征数 | RMSE | MAE |",
        "|------|--------|------|-----|",
        f"| v2.0 (AKShare) | {len(LSTM_V2_FEATURE_NAMES)} | {eval_metrics['rmse']:.4f} | {eval_metrics['mae']:.4f} |",
    ]
    if baseline:
        compare_lines.append(
            f"| v1 (lstm_cycle) | {len(baseline['features'])} | {baseline['rmse']:.4f} | {baseline['mae']:.4f} |"
        )
        rmse_delta = eval_metrics["rmse"] - baseline["rmse"]
        mae_delta = eval_metrics["mae"] - baseline["mae"]
        compare_lines.extend([
            "",
            "## 变化",
            f"- RMSE: {'降低' if rmse_delta < 0 else '升高'} {abs(rmse_delta):.4f}",
            f"- MAE: {'降低' if mae_delta < 0 else '升高'} {abs(mae_delta):.4f}",
        ])
    LSTM_V2_COMPARE_REPORT.write_text("\n".join(compare_lines), encoding="utf-8")

    print(f"[LSTM v2] 模型已保存: {LSTM_V2_MODEL_PATH}")
    print(f"[LSTM v2] RMSE={eval_metrics['rmse']:.4f}, MAE={eval_metrics['mae']:.4f}")
    print(f"[LSTM v2] 报告: {LSTM_V2_EVAL_REPORT}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="训练 LSTM v2.0")
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS_V2)
    parser.add_argument("--epochs", type=int, default=LSTM_EPOCHS)
    parser.add_argument("--refresh", action="store_true", help="强制重新拉取数据")
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    train_lstm_v2(stock_limit=limit, years=args.years, epochs=args.epochs, force_refresh=args.refresh)


if __name__ == "__main__":
    main()
