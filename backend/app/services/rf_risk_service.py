"""随机森林风险评级推理服务（rf_risk.pkl v2.1）"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from app.config import RF_RISK_MODEL
from training.feature_engineering import add_technical_indicators

BACKEND_DIR = Path(__file__).resolve().parents[2]
FEATURE_NAMES = [
    "volatility", "turnover_rate", "pe_percentile", "pb_percentile",
    "volume_change_rate", "amplitude",
    "rsi_14", "ma5_bias", "ma20_bias", "bollinger_width", "vol_ma5_ratio",
]
LABEL_NAMES = ["低风险", "中风险", "高风险"]


class RFRiskPredictor:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = BACKEND_DIR / (model_path or RF_RISK_MODEL)
        self.bundle = None
        self._loaded = False

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return True
        if not self.model_path.exists():
            return False
        try:
            self.bundle = joblib.load(self.model_path)
            self._loaded = True
            return True
        except Exception as e:
            print(f"[RF] 加载失败: {e}")
            return False

    def _features_from_history(self, history: pd.DataFrame) -> Optional[np.ndarray]:
        g = add_technical_indicators(history.sort_values("trade_date").copy())
        g["close"] = pd.to_numeric(g["close"], errors="coerce")
        g["vol"] = pd.to_numeric(g.get("vol"), errors="coerce")
        g["pe"] = pd.to_numeric(g.get("pe"), errors="coerce")
        g["pb"] = pd.to_numeric(g.get("pb"), errors="coerce")
        g["turnover_rate"] = pd.to_numeric(g.get("turnover_rate"), errors="coerce")

        g["return"] = g["close"].pct_change()
        volatility = g["return"].tail(20).std()
        volume_change_rate = g["vol"].pct_change().iloc[-1] if len(g) > 1 else 0

        pe_series = g["pe"].dropna()
        pe_percentile = float(g["pe_percentile"].iloc[-1]) if "pe_percentile" in g.columns and g["pe_percentile"].notna().any() else 0.5
        if pe_percentile == 0.5 and len(pe_series) >= 10:
            pe_percentile = float(pe_series.rank().iloc[-1] / len(pe_series))

        pb_series = g["pb"].dropna()
        pb_percentile = float(g["pb_percentile"].iloc[-1]) if "pb_percentile" in g.columns and g["pb_percentile"].notna().any() else 0.5
        if pb_percentile == 0.5 and len(pb_series) >= 10:
            pb_percentile = float(pb_series.rank().iloc[-1] / len(pb_series))

        turnover = g["turnover_rate"].iloc[-1] if g["turnover_rate"].notna().any() else 1.0
        if pd.isna(turnover):
            vol_ma = g["vol"].rolling(20, min_periods=1).mean().iloc[-1]
            turnover = float(g["vol"].iloc[-1] / vol_ma) if vol_ma else 1.0

        if "amplitude" in g.columns and g["amplitude"].notna().any():
            amplitude = float(g["amplitude"].iloc[-1])
        elif "high" in g.columns and "low" in g.columns:
            pre = float(g.get("pre_close", g["close"].shift(1)).iloc[-1] or g["close"].iloc[-1])
            amplitude = float((g["high"].iloc[-1] - g["low"].iloc[-1]) / pre * 100) if pre else 0.0
        else:
            amplitude = float(abs(g["return"].iloc[-1] or 0) * 100)

        row = g.iloc[-1]
        if pd.isna(volatility):
            return None

        names = self.bundle.get("feature_names", FEATURE_NAMES) if self.bundle else FEATURE_NAMES
        values = {
            "volatility": float(volatility),
            "turnover_rate": float(turnover),
            "pe_percentile": pe_percentile,
            "pb_percentile": pb_percentile,
            "volume_change_rate": float(volume_change_rate) if pd.notna(volume_change_rate) else 0.0,
            "amplitude": amplitude,
            "rsi_14": float(row.get("rsi_14", 50.0)),
            "ma5_bias": float(row.get("ma5_bias", 0.0)),
            "ma20_bias": float(row.get("ma20_bias", 0.0)),
            "bollinger_width": float(row.get("bollinger_width", 0.0)),
            "vol_ma5_ratio": float(row.get("vol_ma5_ratio", 1.0)),
        }
        return np.array([[values[n] for n in names]])

    def predict_asset_risk(self, history: pd.DataFrame) -> Dict[str, Any]:
        if not self._ensure_loaded():
            return {"available": False, "risk_level": "中风险", "risk_label": 1}

        model = self.bundle["model"]
        feat = self._features_from_history(history)
        if feat is None:
            return {"available": False, "risk_level": "中风险", "risk_label": 1}

        label = int(model.predict(feat)[0])
        proba = model.predict_proba(feat)[0] if hasattr(model, "predict_proba") else None
        level = LABEL_NAMES[label] if 0 <= label < len(LABEL_NAMES) else "中风险"
        feat_names = self.bundle.get("feature_names", FEATURE_NAMES)

        return {
            "available": True,
            "risk_level": level,
            "risk_label": label,
            "confidence": round(float(max(proba)), 3) if proba is not None else 0.7,
            "features": {n: round(float(feat[0][i]), 4) for i, n in enumerate(feat_names)},
        }

    def assess_portfolio(self, assets_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对多只资产历史数据做风险评级汇总"""
        results = []
        for item in assets_history:
            code = item.get("code") or item.get("ts_code")
            hist = item.get("history") or []
            if not hist:
                continue
            df = pd.DataFrame(hist)
            pred = self.predict_asset_risk(df)
            results.append({"code": code, **pred})

        if not results:
            return {"available": False, "assets": [], "portfolio_risk": "中风险"}

        labels = [r.get("risk_label", 1) for r in results if r.get("available")]
        avg_label = int(round(sum(labels) / len(labels))) if labels else 1
        portfolio_risk = LABEL_NAMES[avg_label] if 0 <= avg_label < len(LABEL_NAMES) else "中风险"

        return {
            "available": True,
            "assets": results,
            "portfolio_risk": portfolio_risk,
            "portfolio_risk_label": avg_label,
        }


_rf_predictor: Optional[RFRiskPredictor] = None


def get_rf_predictor() -> RFRiskPredictor:
    global _rf_predictor
    if _rf_predictor is None:
        _rf_predictor = RFRiskPredictor()
    return _rf_predictor


def reload_rf_predictor() -> None:
    global _rf_predictor
    _rf_predictor = None
