"""训练配置 — 可通过环境变量覆盖"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data" / "training"
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = MODELS_DIR / "reports"

# 快速跑通：20 只股票 + 2 年；全量：TRAIN_STOCK_LIMIT=300 TRAIN_YEARS=3
STOCK_LIMIT = int(os.getenv("TRAIN_STOCK_LIMIT", "20"))
TRAIN_YEARS = int(os.getenv("TRAIN_YEARS", "2"))
HS300_INDEX = os.getenv("HS300_INDEX", "399300.SZ")

LSTM_MODEL_PATH = MODELS_DIR / "lstm_cycle.h5"
LSTM_SCALER_PATH = MODELS_DIR / "lstm_cycle_scaler.pkl"
LSTM_LOSS_PLOT = REPORTS_DIR / "lstm_loss_curve.png"
LSTM_EVAL_REPORT = REPORTS_DIR / "evaluation_lstm.md"

RF_MODEL_PATH = MODELS_DIR / "rf_risk.pkl"
RF_IMPORTANCE_PLOT = REPORTS_DIR / "rf_feature_importance.png"
RF_EVAL_REPORT = REPORTS_DIR / "evaluation_rf.md"

LSTM_SEQ_LEN = 30
LSTM_PRED_LEN = 5
LSTM_EPOCHS = int(os.getenv("LSTM_EPOCHS", "30"))
LSTM_BATCH_SIZE = int(os.getenv("LSTM_BATCH_SIZE", "64"))

RF_N_ESTIMATORS = int(os.getenv("RF_N_ESTIMATORS", "100"))
RF_FORWARD_DAYS = 20  # 用于标签：未来 N 日收益率

SKIP_DAILY_BASIC = os.getenv("SKIP_DAILY_BASIC", "1") == "1"
TUSHARE_TOKEN = os.getenv(
    "TUSHARE_TOKEN",
    "323c3aa4a72205441336067dca690bc3918112710e224e1818456d29",
)

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
