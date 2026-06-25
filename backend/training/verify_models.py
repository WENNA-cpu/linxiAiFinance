"""快速验证 LSTM v2.0 / RF 生产模型指标"""
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import load_model

from training.config import RF_SPRINT_FEATURE_NAMES
from training.data_fetch import prepare_training_data
from training.feature_engineering import build_feature_matrix_v2
from training.train_lstm_v2 import build_sequences
from training.train_rf_sprint import engineer_features_sprint

df = prepare_training_data(stock_limit=20, years=3, feature_version="v2")
df["close"] = df["close"].astype(float)

x_all, y_all = [], []
for _, g in df.groupby("ts_code"):
    try:
        m = build_feature_matrix_v2(g)
        x, y = build_sequences(m, 30, 5, close_idx=0)
        if len(x):
            x_all.append(x)
            y_all.append(y)
    except ValueError:
        pass

X = np.concatenate(x_all)
Y = np.concatenate(y_all)
bundle = joblib.load("models/lstm_cycle_scaler.pkl")
fs, ts = bundle["feature_scaler"], bundle["target_scaler"]
ns, sl, nf = X.shape
Xs = fs.transform(X.reshape(-1, nf)).reshape(ns, sl, nf)
Ys = ts.transform(Y.reshape(-1, 1)).reshape(Y.shape)
_, X_test, _, y_test = train_test_split(Xs, Ys, test_size=0.2, random_state=42)
model = load_model("models/lstm_cycle.h5", compile=False)
pred = model.predict(X_test, verbose=0)
yt = ts.inverse_transform(y_test.reshape(-1, 1)).reshape(y_test.shape)
yp = ts.inverse_transform(pred.reshape(-1, 1)).reshape(pred.shape)
print(f"LSTM RMSE={np.sqrt(mean_squared_error(yt, yp)):.4f} MAE={mean_absolute_error(yt, yp):.4f}")

frames = []
for _, g in df.groupby("ts_code"):
    f = engineer_features_sprint(g)
    if not f.empty:
        frames.append(f)
data = pd.concat(frames, ignore_index=True)
feat_names = RF_SPRINT_FEATURE_NAMES
Xrf = data[feat_names].astype(float).values
yrf = data["risk_label"].astype(int).values
b = joblib.load("models/rf_risk.pkl")
bundle_feats = b.get("feature_names", feat_names)
Xrf = data[bundle_feats].astype(float).values
_, X_test_rf, _, y_test_rf = train_test_split(Xrf, yrf, test_size=0.2, random_state=42, stratify=yrf)
print(f"RF accuracy={b['model'].score(X_test_rf, y_test_rf):.4f} version={b.get('version')}")
