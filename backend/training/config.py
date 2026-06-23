"""训练配置 — 可通过环境变量覆盖"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data" / "training"
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = MODELS_DIR / "reports"

# 快速跑通：20 只股票 + 5 年；全量：TRAIN_STOCK_LIMIT=300 TRAIN_YEARS=5
STOCK_LIMIT = int(os.getenv("TRAIN_STOCK_LIMIT", "20"))
TRAIN_YEARS = int(os.getenv("TRAIN_YEARS", "5"))
HS300_INDEX = os.getenv("HS300_INDEX", "399300.SZ")
PERCENTILE_WINDOW = int(os.getenv("PERCENTILE_WINDOW", "252"))

LSTM_FEATURE_NAMES = ["close", "pct_chg", "vol", "pe_pct", "pb_pct"]
LSTM_N_FEATURES = len(LSTM_FEATURE_NAMES)

LSTM_MODEL_PATH = MODELS_DIR / "lstm_cycle.h5"
LSTM_SCALER_PATH = MODELS_DIR / "lstm_cycle_scaler.pkl"
LSTM_BASELINE_MODEL_PATH = MODELS_DIR / "lstm_cycle_baseline.h5"
LSTM_BASELINE_SCALER_PATH = MODELS_DIR / "lstm_cycle_baseline_scaler.pkl"
LSTM_LOSS_PLOT = REPORTS_DIR / "lstm_loss_curve.png"
LSTM_EVAL_REPORT = REPORTS_DIR / "evaluation_lstm.md"
LSTM_COMPARE_REPORT = REPORTS_DIR / "evaluation_lstm_comparison.md"

RF_MODEL_PATH = MODELS_DIR / "rf_risk.pkl"
RF_IMPORTANCE_PLOT = REPORTS_DIR / "rf_feature_importance.png"
RF_EVAL_REPORT = REPORTS_DIR / "evaluation_rf.md"

LSTM_SEQ_LEN = 30
LSTM_PRED_LEN = 5
LSTM_EPOCHS = int(os.getenv("LSTM_EPOCHS", "30"))
LSTM_BATCH_SIZE = int(os.getenv("LSTM_BATCH_SIZE", "64"))

LSTM_V2_MODEL_PATH = MODELS_DIR / "lstm_v2.0.h5"
LSTM_V2_SCALER_PATH = MODELS_DIR / "lstm_v2.0_scaler.pkl"
LSTM_V2_FEATURE_NAMES = [
    "close", "pct_chg", "vol", "pe_pct", "pb_pct", "turnover_rate", "amplitude",
]
LSTM_V2_N_FEATURES = len(LSTM_V2_FEATURE_NAMES)
LSTM_V2_LOSS_PLOT = REPORTS_DIR / "lstm_v2_loss_curve.png"
LSTM_V2_EVAL_REPORT = REPORTS_DIR / "evaluation_lstm_v2.md"
LSTM_V2_COMPARE_REPORT = REPORTS_DIR / "evaluation_lstm_v2_comparison.md"

RF_V2_FEATURE_NAMES = [
    "volatility", "turnover_rate", "pe_percentile", "pb_percentile",
    "volume_change_rate", "amplitude",
]

# 生产随机森林特征（v2.1）
RF_FEATURE_NAMES = RF_V2_FEATURE_NAMES + [
    "rsi_14", "ma5_bias", "ma20_bias", "bollinger_width", "vol_ma5_ratio",
]

TRAIN_YEARS_V2 = int(os.getenv("TRAIN_YEARS_V2", "3"))

RF_N_ESTIMATORS = int(os.getenv("RF_N_ESTIMATORS", "100"))
RF_FORWARD_DAYS = 20  # 用于标签：未来 N 日收益率

SKIP_DAILY_BASIC = os.getenv("SKIP_DAILY_BASIC", "0") == "1"
TUSHARE_TOKEN = os.getenv(
    "TUSHARE_TOKEN",
    "323c3aa4a72205441336067dca690bc3918112710e224e1818456d29",
)

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
