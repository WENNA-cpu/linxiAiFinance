from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, timedelta
import numpy as np

from app.models.database import get_db
from app.services.ai_service import AIService, ModelTrainingService
from app.services.data_service import DataService
from app.services.lstm_cycle_service import get_lstm_predictor
from app.services.model_manager import should_use_new_model
from app.config import NEW_MODEL_RATIO

router = APIRouter()


class CycleAnalysisInput(BaseModel):
    asset_code: str
    time_range: str = "3y"


class CycleAnalyzeInput(BaseModel):
    ts_code: str


class ModelTrainingInput(BaseModel):
    ts_code: str
    epochs: int = 50


TIME_RANGE_DAYS = {
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "3y": 365 * 3,
}


def normalize_ts_code(code: str) -> str:
    if "." in code:
        return code
    if code.startswith("6"):
        return f"{code}.SH"
    return f"{code}.SZ"


def calculate_percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(values, percentile))


def determine_interval(current: float, p30: float, p70: float) -> tuple:
    if current < p30:
        return "低估区间", "小幅加仓"
    if current > p70:
        return "高估区间", "小幅减仓"
    return "合理区间", "持有观望"


async def fetch_close_prices(ts_code: str, days: int = 365 * 3) -> List[float]:
    data_service = DataService()
    end = datetime.now()
    start = end - timedelta(days=days)
    rows = await data_service.fetch_daily_data(
        ts_code, start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    )
    if not rows:
        return []
    rows = sorted(rows, key=lambda x: x.get("trade_date", ""))
    return [float(r["close"]) for r in rows if r.get("close")]


async def run_lstm_forecast(ts_code: str, use_new: bool) -> Dict[str, Any]:
    closes = await fetch_close_prices(ts_code)
    if len(closes) < 30:
        return {"available": False, "reason": "收盘价历史不足"}
    predictor = get_lstm_predictor(use_new=use_new)
    result = predictor.predict(closes)
    result["model_variant"] = "new" if use_new else "legacy"
    return result


async def analyze_pe_pb(ts_code: str, time_range: str = "3y") -> Dict[str, Any]:
    """基于 Tushare PE/PB 分位数的周期分析 + LSTM 价格预测"""
    data_service = DataService()
    ts_code = normalize_ts_code(ts_code)
    days = TIME_RANGE_DAYS.get(time_range, 365 * 3)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    daily_basic_list = await data_service.fetch_daily_basic_historical(
        ts_code,
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d"),
    )

    if not daily_basic_list or len(daily_basic_list) < 30:
        raise HTTPException(
            status_code=404,
            detail=f"无法从 Tushare 获取 {ts_code} 的估值历史数据，请检查股票代码或 API Token",
        )

    pe_values: List[float] = []
    pb_values: List[float] = []
    pe_history: List[Dict[str, Any]] = []
    pb_history: List[Dict[str, Any]] = []

    for item in daily_basic_list:
        pe = item.get("pe")
        pb = item.get("pb")
        trade_date = item.get("trade_date", "")
        formatted_date = (
            f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            if trade_date and len(trade_date) == 8
            else trade_date
        )

        if pe and pe > 0:
            pe_values.append(float(pe))
            pe_history.append({"date": formatted_date, "value": round(float(pe), 2)})
        if pb and pb > 0:
            pb_values.append(float(pb))
            pb_history.append({"date": formatted_date, "value": round(float(pb), 2)})

    if len(pe_values) < 10:
        raise HTTPException(status_code=404, detail=f"{ts_code} 历史估值数据不足，无法分析")

    pe_30 = calculate_percentile(pe_values, 30)
    pe_70 = calculate_percentile(pe_values, 70)
    pb_30 = calculate_percentile(pb_values, 30) if pb_values else 0.0
    pb_70 = calculate_percentile(pb_values, 70) if pb_values else 0.0
    current_pe = pe_values[0]
    current_pb = pb_values[0] if pb_values else 0.0
    interval, suggestion = determine_interval(current_pe, pe_30, pe_70)

    stock_name = ts_code.split(".")[0]
    try:
        stock_basic = await data_service.fetch_stock_basic()
        if stock_basic:
            for stock in stock_basic:
                if stock.get("ts_code") == ts_code:
                    stock_name = stock.get("name", stock_name)
                    break
    except Exception:
        pass

    use_new = should_use_new_model(ts_code, NEW_MODEL_RATIO)
    lstm_result = await run_lstm_forecast(ts_code, use_new=use_new)

    history_limit = min(len(pe_history), 500)
    response = {
        "ts_code": ts_code,
        "name": stock_name,
        "current_pe": round(current_pe, 2),
        "current_pb": round(current_pb, 2),
        "pe_30_percentile": round(pe_30, 2),
        "pe_70_percentile": round(pe_70, 2),
        "pb_30_percentile": round(pb_30, 2),
        "pb_70_percentile": round(pb_70, 2),
        "interval": interval,
        "suggestion": suggestion,
        "pe_history": pe_history[:history_limit],
        "pb_history": pb_history[:history_limit],
        "time_range": time_range,
        "data_source": "Tushare估值数据 + LSTM周期模型",
        "lstm_forecast": lstm_result,
        "model_routing": {
            "use_new_model": use_new,
            "gray_ratio": NEW_MODEL_RATIO,
            "variant": lstm_result.get("model_variant", "new"),
        },
    }

    if lstm_result.get("available"):
        ci = lstm_result.get("confidence_interval", {})
        response["price_forecast"] = {
            "current_price": lstm_result.get("current_price"),
            "predicted_prices": lstm_result.get("predicted_prices"),
            "predicted_change_pct": lstm_result.get("change_pct"),
            "trend": lstm_result.get("trend"),
            "confidence_interval": ci,
        }

    return response


@router.post("/analyze")
async def analyze_cycle(data: CycleAnalysisInput, db: Session = Depends(get_db)):
    """资产周期分析 - PE/PB 分位 + LSTM 价格预测"""
    return await analyze_pe_pb(data.asset_code, data.time_range)


@router.post("/analyze-new")
async def analyze_cycle_new(data: CycleAnalyzeInput, db: Session = Depends(get_db)):
    return await analyze_pe_pb(data.ts_code, "3y")


@router.post("/train")
async def train_cycle_model(data: ModelTrainingInput, db: Session = Depends(get_db)):
    training_service = ModelTrainingService()
    result = await training_service.train_lstm_model(data.ts_code, data.epochs)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/forecast/{asset_code}")
async def get_forecast(asset_code: str, days: int = 30, db: Session = Depends(get_db)):
    ts_code = normalize_ts_code(asset_code)
    use_new = should_use_new_model(ts_code, NEW_MODEL_RATIO)
    lstm_result = await run_lstm_forecast(ts_code, use_new=use_new)
    if not lstm_result.get("available"):
        ai_service = AIService()
        result = await ai_service.analyze_cycle(asset_code)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {
            "asset_code": asset_code,
            "forecast_days": days,
            "forecast": result.get("lstm_forecast", {}),
            "current_phase": result.get("current_phase"),
            "recommendation": result.get("recommendation"),
            "fallback": True,
        }
    return {
        "asset_code": asset_code,
        "forecast_days": days,
        "forecast": lstm_result,
        "model_variant": lstm_result.get("model_variant"),
    }
