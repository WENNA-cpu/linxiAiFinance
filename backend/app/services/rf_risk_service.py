"""随机森林风险评级推理服务（rf_risk.pkl）"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from app.config import RF_RISK_MODEL

BACKEND_DIR = Path(__file__).resolve().parents[2]
FEATURE_NAMES = ["volatility", "turnover_rate", "pe_percentile", "volume_change_rate"]
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
        g = history.sort_values("trade_date").copy()
        g["close"] = pd.to_numeric(g["close"], errors="coerce")
        g["vol"] = pd.to_numeric(g.get("vol"), errors="coerce")
        g["pe"] = pd.to_numeric(g.get("pe"), errors="coerce")
        g["turnover_rate"] = pd.to_numeric(g.get("turnover_rate"), errors="coerce")

        g["return"] = g["close"].pct_change()
        volatility = g["return"].tail(20).std()
        volume_change_rate = g["vol"].pct_change().iloc[-1] if len(g) > 1 else 0
        pe_series = g["pe"].dropna()
        pe_percentile = 0.5
        if len(pe_series) >= 10:
            pe_percentile = (pe_series.rank().iloc[-1] / len(pe_series))
        turnover = g["turnover_rate"].iloc[-1] if "turnover_rate" in g.columns else 0
        if pd.isna(turnover):
            turnover = g["turnover_rate"].median() if g["turnover_rate"].notna().any() else 0

        if pd.isna(volatility):
            return None
        return np.array([[float(volatility), float(turnover), float(pe_percentile), float(volume_change_rate)]])

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

        return {
            "available": True,
            "risk_level": level,
            "risk_label": label,
            "confidence": round(float(max(proba)), 3) if proba is not None else 0.7,
            "features": {n: round(float(feat[0][i]), 4) for i, n in enumerate(FEATURE_NAMES)},
        }

    def assess_portfolio(self, assets_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对多只资产历史数据做风险评级汇总"""
        results = []
        high_risk = 0
        for item in assets_history:
            hist = item.get("history")
            if hist is None or len(hist) < 30:
                continue
            df = pd.DataFrame(hist)
            pred = self.predict_asset_risk(df)
            pred["code"] = item.get("code")
            pred["name"] = item.get("name")
            results.append(pred)
            if pred.get("risk_level") == "高风险":
                high_risk += 1

        return {
            "asset_predictions": results,
            "high_risk_count": high_risk,
            "total_scored": len(results),
            "model_available": self._ensure_loaded(),
        }


_rf_predictor: Optional[RFRiskPredictor] = None


def get_rf_predictor() -> RFRiskPredictor:
    global _rf_predictor
    if _rf_predictor is None:
        _rf_predictor = RFRiskPredictor()
    return _rf_predictor
