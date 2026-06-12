"""LSTM 周期预测推理服务（lstm_cycle.h5）"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

from app.config import LSTM_CYCLE_MODEL, LSTM_CYCLE_SCALER, LSTM_LEGACY_MODEL

BACKEND_DIR = Path(__file__).resolve().parents[2]
LSTM_SEQ_LEN = 30
LSTM_PRED_LEN = 5
FEATURE_NAMES = ["close", "pct_chg", "vol", "pe_pct", "pb_pct"]


class LSTMCyclePredictor:
    def __init__(self, model_path: Optional[str] = None, scaler_path: Optional[str] = None):
        self.model_path = BACKEND_DIR / (model_path or LSTM_CYCLE_MODEL)
        self.scaler_path = BACKEND_DIR / (scaler_path or LSTM_CYCLE_SCALER)
        self.model = None
        self.feature_scaler = None
        self.target_scaler = None
        self.legacy_scaler = None
        self.n_features = 1
        self._loaded = False

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return True
        if not self.model_path.exists():
            return False
        try:
            self.model = load_model(self.model_path, compile=False)
            if self.scaler_path.exists():
                bundle = joblib.load(self.scaler_path)
                if isinstance(bundle, dict) and "feature_scaler" in bundle:
                    self.feature_scaler = bundle["feature_scaler"]
                    self.target_scaler = bundle["target_scaler"]
                    self.n_features = int(bundle.get("n_features", len(FEATURE_NAMES)))
                else:
                    self.legacy_scaler = bundle
                    self.n_features = 1
            self._loaded = True
            return True
        except Exception as e:
            print(f"[LSTM] 加载失败: {e}")
            return False

    def predict(
        self,
        close_prices: Optional[List[float]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self._ensure_loaded():
            return {"error": "LSTM 模型未训练或加载失败", "available": False}

        if self.n_features > 1 and history:
            return self._predict_multifeature(history)
        if close_prices:
            return self._predict_legacy(close_prices)
        if history:
            closes = [float(r["close"]) for r in history if r.get("close") is not None]
            return self._predict_legacy(closes)
        return {"error": "缺少预测输入", "available": False}

    def _predict_legacy(self, close_prices: List[float]) -> Dict[str, Any]:
        if len(close_prices) < LSTM_SEQ_LEN:
            return {"error": f"需要至少 {LSTM_SEQ_LEN} 天收盘价", "available": False}

        seq = np.array(close_prices[-LSTM_SEQ_LEN:], dtype=float).reshape(-1, 1)
        scaler = self.legacy_scaler or self.feature_scaler or self.target_scaler
        if scaler is not None:
            seq_scaled = scaler.transform(seq).reshape(1, LSTM_SEQ_LEN, 1)
            pred_scaled = self.model.predict(seq_scaled, verbose=0)
            inverse = self.target_scaler or scaler
            pred = inverse.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
        else:
            inp = seq.reshape(1, LSTM_SEQ_LEN, 1)
            pred = self.model.predict(inp, verbose=0).flatten()

        return self._format_result(close_prices, pred)

    def _predict_multifeature(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        from training.feature_engineering import build_feature_matrix

        if len(history) < LSTM_SEQ_LEN + 30:
            return {"error": f"需要至少 {LSTM_SEQ_LEN + 30} 天历史（含估值）", "available": False}

        df = pd.DataFrame(history)
        try:
            matrix = build_feature_matrix(df)
        except ValueError as e:
            return {"error": str(e), "available": False}

        if len(matrix) < LSTM_SEQ_LEN:
            return {"error": f"有效特征长度不足 {LSTM_SEQ_LEN}", "available": False}

        window = matrix[-LSTM_SEQ_LEN:]
        if self.feature_scaler is None or self.target_scaler is None:
            return {"error": "多特征 Scaler 未加载", "available": False}

        scaled = self.feature_scaler.transform(window).reshape(1, LSTM_SEQ_LEN, self.n_features)
        pred_scaled = self.model.predict(scaled, verbose=0)
        pred = self.target_scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()

        closes = [float(r["close"]) for r in history if r.get("close") is not None]
        return self._format_result(closes, pred, multifeature=True)

    def _format_result(
        self,
        close_prices: List[float],
        pred: np.ndarray,
        multifeature: bool = False,
    ) -> Dict[str, Any]:
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
            "feature_mode": "multifeature" if multifeature else "close_only",
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


def reload_lstm_predictors() -> None:
    """回滚或热更新后清空缓存，下次推理重新加载模型文件"""
    global _lstm_new, _lstm_legacy
    _lstm_new = None
    _lstm_legacy = None
