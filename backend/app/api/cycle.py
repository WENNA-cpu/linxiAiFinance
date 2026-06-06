from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import numpy as np

from app.models.database import get_db
from app.services.ai_service import AIService, ModelTrainingService
from app.services.data_service import DataService

router = APIRouter()


class CycleAnalysisInput(BaseModel):
    asset_code: str
    time_range: str = "1y"


class CycleAnalyzeInput(BaseModel):
    ts_code: str


class ModelTrainingInput(BaseModel):
    ts_code: str
    epochs: int = 50


def calculate_percentile(values: List[float], percentile: float) -> float:
    """计算分位数"""
    if not values:
        return 0.0
    return float(np.percentile(values, percentile))


def determine_interval(current: float, p30: float, p70: float) -> tuple:
    """根据当前值和分位数确定区间和建议"""
    if current < p30:
        return "低估区间", "小幅加仓"
    elif current > p70:
        return "高估区间", "小幅减仓"
    else:
        return "合理区间", "持有观望"


@router.post("/analyze")
async def analyze_cycle(data: CycleAnalysisInput, db: Session = Depends(get_db)):
    """资产周期分析 - 使用LSTM模型"""
    ai_service = AIService()
    result = await ai_service.analyze_cycle(data.asset_code, data.time_range)
    return result


@router.post("/analyze-new")
async def analyze_cycle_new(data: CycleAnalyzeInput, db: Session = Depends(get_db)):
    """资产周期分析 - 基于PE/PB分位数的规则判断"""
    data_service = DataService()

    # 获取近3年的估值历史数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 3)

    end_date_str = end_date.strftime("%Y%m%d")
    start_date_str = start_date.strftime("%Y%m%d")

    # 获取历史每日估值数据
    daily_basic_list = await data_service.fetch_daily_basic_historical(
        data.ts_code, start_date_str, end_date_str
    )

    if not daily_basic_list or len(daily_basic_list) < 30:
        # 数据不足，返回模拟数据
        return {
            "ts_code": data.ts_code,
            "name": data.ts_code.split('.')[0],
            "current_pe": 6.85,
            "current_pb": 0.72,
            "pe_30_percentile": 5.2,
            "pe_70_percentile": 8.1,
            "pb_30_percentile": 0.58,
            "pb_70_percentile": 0.85,
            "interval": "低估区间",
            "suggestion": "小幅加仓",
            "pe_history": [{"date": "2024-01-01", "value": 6.5}],
            "pb_history": [{"date": "2024-01-01", "value": 0.68}],
            "is_mock": True
        }

    # 提取PE和PB历史数据
    pe_values = []
    pb_values = []
    pe_history = []
    pb_history = []

    for item in daily_basic_list:
        pe = item.get("pe")
        pb = item.get("pb")
        trade_date = item.get("trade_date", "")

        # 格式化日期
        if trade_date and len(trade_date) == 8:
            formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
        else:
            formatted_date = trade_date

        if pe and pe > 0:
            pe_values.append(float(pe))
            pe_history.append({"date": formatted_date, "value": round(float(pe), 2)})

        if pb and pb > 0:
            pb_values.append(float(pb))
            pb_history.append({"date": formatted_date, "value": round(float(pb), 2)})

    if len(pe_values) < 10:
        return {
            "ts_code": data.ts_code,
            "name": data.ts_code.split('.')[0],
            "current_pe": 0.0,
            "current_pb": 0.0,
            "pe_30_percentile": 0.0,
            "pe_70_percentile": 0.0,
            "pb_30_percentile": 0.0,
            "pb_70_percentile": 0.0,
            "interval": "数据不足",
            "suggestion": "无法判断",
            "pe_history": [],
            "pb_history": [],
            "error": "历史数据不足"
        }

    # 计算分位数
    pe_30 = calculate_percentile(pe_values, 30)
    pe_70 = calculate_percentile(pe_values, 70)
    pb_30 = calculate_percentile(pb_values, 30)
    pb_70 = calculate_percentile(pb_values, 70)

    # 当前估值
    current_pe = pe_values[0] if pe_values else 0.0
    current_pb = pb_values[0] if pb_values else 0.0

    # 确定区间和建议（优先使用PE判断）
    interval, suggestion = determine_interval(current_pe, pe_30, pe_70)

    # 获取股票名称
    stock_name = data.ts_code.split('.')[0]
    try:
        stock_basic = await data_service.fetch_stock_basic()
        if stock_basic:
            for stock in stock_basic:
                if stock.get("ts_code") == data.ts_code:
                    stock_name = stock.get("name", stock_name)
                    break
    except:
        pass

    return {
        "ts_code": data.ts_code,
        "name": stock_name,
        "current_pe": round(current_pe, 2),
        "current_pb": round(current_pb, 2),
        "pe_30_percentile": round(pe_30, 2),
        "pe_70_percentile": round(pe_70, 2),
        "pb_30_percentile": round(pb_30, 2),
        "pb_70_percentile": round(pb_70, 2),
        "interval": interval,
        "suggestion": suggestion,
        "pe_history": pe_history[:100],  # 限制返回数量
        "pb_history": pb_history[:100]
    }


@router.post("/train")
async def train_cycle_model(data: ModelTrainingInput, db: Session = Depends(get_db)):
    """训练LSTM周期分析模型"""
    training_service = ModelTrainingService()
    result = await training_service.train_lstm_model(data.ts_code, data.epochs)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/forecast/{asset_code}")
async def get_forecast(asset_code: str, days: int = 30, db: Session = Depends(get_db)):
    """获取资产价格预测"""
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
    }
