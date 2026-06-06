"""LSTM 周期预测推理服务（lstm_cycle.h5）"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from tensorflow.keras.models import load_model

from app.config import LSTM_CYCLE_MODEL, LSTM_CYCLE_SCALER, LSTM_LEGACY_MODEL

BACKEND_DIR = Path(__file__).resolve().parents[2]
LSTM_SEQ_LEN = 30
LSTM_PRED_LEN = 5


class LSTMCyclePredictor:
    def __init__(self, model_path: Optional[str] = None, scaler_path: Optional[str] = None):
        self.model_path = BACKEND_DIR / (model_path or LSTM_CYCLE_MODEL)
        self.scaler_path = BACKEND_DIR / (scaler_path or LSTM_CYCLE_SCALER)
        self.model = None
        self.scaler = None
        self._loaded = False

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return True
        if not self.model_path.exists():
            return False
        try:
            self.model = load_model(self.model_path, compile=False)
            if self.scaler_path.exists():
                self.scaler = joblib.load(self.scaler_path)
            self._loaded = True
            return True
        except Exception as e:
            print(f"[LSTM] 加载失败: {e}")
            return False

    def predict(self, close_prices: List[float]) -> Dict[str, Any]:
        if not self._ensure_loaded():
            return {"error": "LSTM 模型未训练或加载失败", "available": False}

        if len(close_prices) < LSTM_SEQ_LEN:
            return {"error": f"需要至少 {LSTM_SEQ_LEN} 天收盘价", "available": False}

        seq = np.array(close_prices[-LSTM_SEQ_LEN:], dtype=float).reshape(-1, 1)
        if self.scaler is not None:
            seq_scaled = self.scaler.transform(seq).reshape(1, LSTM_SEQ_LEN, 1)
            pred_scaled = self.model.predict(seq_scaled, verbose=0)
            pred = self.scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
        else:
            inp = seq.reshape(1, LSTM_SEQ_LEN, 1)
            pred = self.model.predict(inp, verbose=0).flatten()

        current = float(close_prices[-1])
        predicted_next = float(pred[0])
        volatility = float(np.std(close_prices[-30:])) if len(close_prices) >= 30 else current * 0.02

        return {
            "available": True,
            "current_price": round(current, 2),
            "predicted_prices": [round(float(p), 2) for p in pred[:LSTM_PRED_LEN]],
            "predicted_next": round(predicted_next, 2),
            "change_pct": round((predicted_next - current) / current * 100, 2) if current else 0,
            "trend": "up" if predicted_next > current else "down",
            "confidence_interval": {
                "low": round(predicted_next - 1.96 * volatility, 2),
                "high": round(predicted_next + 1.96 * volatility, 2),
            },
            "forecast_horizon_days": LSTM_PRED_LEN,
        }


_lstm_new: Optional[LSTMCyclePredictor] = None
_lstm_legacy: Optional[LSTMCyclePredictor] = None


def get_lstm_predictor(use_new: bool = True) -> LSTMCyclePredictor:
    global _lstm_new, _lstm_legacy
    if use_new:
        if _lstm_new is None:
            _lstm_new = LSTMCyclePredictor()
        return _lstm_new
    if _lstm_legacy is None:
        _lstm_legacy = LSTMCyclePredictor(model_path=LSTM_LEGACY_MODEL, scaler_path=LSTM_LEGACY_MODEL.replace(".h5", "_scaler.json"))
    return _lstm_legacy
