"""应用配置"""
import os

# 灰度：NEW_MODEL_RATIO=5 表示约 5% 流量使用新模型
NEW_MODEL_RATIO = int(os.getenv("NEW_MODEL_RATIO", "5"))

# 模型路径（相对于 backend 目录）
LSTM_CYCLE_MODEL = os.getenv("LSTM_CYCLE_MODEL", "models/lstm_cycle.h5")
LSTM_CYCLE_SCALER = os.getenv("LSTM_CYCLE_SCALER", "models/lstm_cycle_scaler.pkl")
LSTM_LEGACY_MODEL = os.getenv("LSTM_LEGACY_MODEL", "models/saved/lstm_model.h5")

RF_RISK_MODEL = os.getenv("RF_RISK_MODEL", "models/rf_risk.pkl")
RF_LEGACY_MODEL = os.getenv("RF_LEGACY_MODEL", "models/saved/risk_model.pkl")

MODEL_METADATA_PATH = os.getenv("MODEL_METADATA_PATH", "models/model_metadata.json")
