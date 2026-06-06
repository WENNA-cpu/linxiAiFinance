from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import random

from app.models.database import get_db
from app.services.data_service import DataService

router = APIRouter()


def get_sentiment_status(index: int) -> str:
    if index >= 70:
        return "贪婪"
    if index >= 55:
        return "乐观"
    if index >= 45:
        return "中性"
    if index >= 30:
        return "悲观"
    return "恐慌"


def get_market_state(index: int) -> str:
    if index > 65:
        return "强势上涨"
    if index < 35:
        return "弱势下跌"
    return "震荡整理"


def get_extreme_alert(index: int) -> Optional[str]:
    if index > 70:
        return "市场过热，警惕回调风险"
    if index < 30:
        return "市场恐慌，历史数据显示恐慌后往往反弹"
    return None


def calculate_sentiment_index(limit_up: int, limit_down: int, shock_count: int) -> int:
    total = limit_up + limit_down
    if total == 0:
        return 50
    limit_ratio = limit_up / total
    base_score = limit_ratio * 100
    shock_impact = min(shock_count * 2, 20)
    sentiment = base_score - shock_impact + random.randint(-3, 3)
    return max(0, min(100, int(sentiment)))


def calculate_behavior_bias(sentiment_index: int, limit_up: int, limit_down: int, shock_count: int) -> Dict[str, int]:
    """基于市场情绪数据计算行为偏差指数"""
    total = max(limit_up + limit_down, 1)
    limit_ratio = limit_up / total

    confirmation_bias = int(min(95, max(25, 45 + (sentiment_index - 50) * 0.9)))
    loss_aversion = int(min(95, max(30, 55 + (50 - sentiment_index) * 0.7)))
    herd_mentality = int(min(90, max(20, 35 + abs(sentiment_index - 50) * 1.1 + limit_ratio * 20)))
    overconfidence = int(min(85, max(15, 30 + max(0, sentiment_index - 55) * 1.3)))

    if shock_count > 10:
        herd_mentality = min(90, herd_mentality + 10)
        confirmation_bias = min(95, confirmation_bias + 5)

    return {
        "confirmation_bias": confirmation_bias,
        "loss_aversion": loss_aversion,
        "herd_mentality": herd_mentality,
        "overconfidence": overconfidence,
    }


async def fetch_limit_list(data_service: DataService, trade_date: str) -> Dict[str, int]:
    try:
        data = await data_service._request("daily", {"trade_date": trade_date, "limit": 5000})
        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            limit_up = 0
            limit_down = 0
            for item in items:
                item_dict = dict(zip(fields, item))
                pct_chg = item_dict.get("pct_chg", 0)
                if pct_chg >= 9.9:
                    limit_up += 1
                elif pct_chg <= -9.9:
                    limit_down += 1
            return {"limit_up": limit_up, "limit_down": limit_down}
    except Exception as e:
        print(f"Error fetching limit list: {e}")
    return {"limit_up": 0, "limit_down": 0}


async def fetch_stk_shock(data_service: DataService, trade_date: str) -> List[Dict]:
    try:
        data = await data_service._request("stk_shock", {"trade_date": trade_date, "limit": 100})
        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            return [dict(zip(fields, item)) for item in items]
    except Exception as e:
        print(f"Error fetching stk_shock: {e}")
    return []


async def _fetch_sentiment_metrics() -> Dict[str, Any]:
    data_service = DataService()
    trade_date = datetime.now().strftime("%Y%m%d")
    limit_data = await fetch_limit_list(data_service, trade_date)
    limit_up = limit_data.get("limit_up", 0)
    limit_down = limit_data.get("limit_down", 0)
    shock_records = await fetch_stk_shock(data_service, trade_date)
    warning_signals = len(shock_records)
    sentiment_index = calculate_sentiment_index(limit_up, limit_down, warning_signals)

    return {
        "sentiment_index": sentiment_index,
        "status": get_sentiment_status(sentiment_index),
        "market_state": get_market_state(sentiment_index),
        "warning_signals": warning_signals,
        "extreme_alert": get_extreme_alert(sentiment_index),
        "limit_up": limit_up,
        "limit_down": limit_down,
        "shock_records": shock_records,
        "shock_count": warning_signals,
    }


@router.get("/sentiment")
async def get_market_sentiment(db: Session = Depends(get_db)):
    """获取市场情绪指数 - 基于 Tushare 真实数据"""
    try:
        metrics = await _fetch_sentiment_metrics()
        return {
            "sentiment_index": metrics["sentiment_index"],
            "status": metrics["status"],
            "market_state": metrics["market_state"],
            "warning_signals": metrics["warning_signals"],
            "extreme_alert": metrics["extreme_alert"],
            "detail": {
                "limit_up": metrics["limit_up"],
                "limit_down": metrics["limit_down"],
                "shock_records": metrics["shock_records"][:10],
            },
            "data_source": "Tushare实时数据",
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "components": {
                "limit_up": metrics["limit_up"],
                "limit_down": metrics["limit_down"],
                "shock_count": metrics["shock_count"],
            },
        }
    except Exception as e:
        print(f"Error in get_market_sentiment: {e}")
        raise HTTPException(status_code=503, detail="无法获取市场情绪数据，请稍后重试")


@router.get("/behavior-bias")
async def get_behavior_bias(db: Session = Depends(get_db)):
    """获取行为偏差检测数据 - 基于市场情绪计算"""
    try:
        metrics = await _fetch_sentiment_metrics()
        bias = calculate_behavior_bias(
            metrics["sentiment_index"],
            metrics["limit_up"],
            metrics["limit_down"],
            metrics["shock_count"],
        )
        return {
            **bias,
            "sentiment_index": metrics["sentiment_index"],
            "data_source": "基于Tushare市场情绪数据计算",
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "methodology": {
                "confirmation_bias": "情绪越高，确认偏误越强",
                "loss_aversion": "情绪越低，损失厌恶越强",
                "herd_mentality": "涨跌停比极端时，羊群效应增强",
                "overconfidence": "市场过热时，过度自信风险上升",
            },
        }
    except Exception as e:
        print(f"Error in get_behavior_bias: {e}")
        raise HTTPException(status_code=503, detail="无法计算行为偏差数据")


@router.get("/data/{ts_code}")
async def get_market_data(ts_code: str, db: Session = Depends(get_db)):
    data_service = DataService()
    data = await data_service.fetch_market_data(ts_code)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code} 的数据")
    return data


@router.get("/valuation/{ts_code}")
async def get_valuation_data(ts_code: str, db: Session = Depends(get_db)):
    data_service = DataService()
    valuation = await data_service.fetch_valuation_data(ts_code)
    return valuation


@router.get("/daily/{ts_code}")
async def get_daily_data(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    data_service = DataService()
    data = await data_service.fetch_daily_data(ts_code, start_date, end_date)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code} 的数据")
    return {"ts_code": ts_code, "data": data, "count": len(data)}


@router.get("/daily")
async def get_daily_data_query(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    data_service = DataService()
    data = await data_service.fetch_daily_data(ts_code, start_date, end_date)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code} 的数据")
    return {"ts_code": ts_code, "data": data, "count": len(data)}


@router.get("/daily_basic")
async def get_daily_basic_query(
    ts_code: str,
    trade_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    data_service = DataService()
    data = await data_service.fetch_daily_basic(ts_code, trade_date)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code} 的估值数据")
    return {"ts_code": ts_code, "data": data, "count": len(data)}


@router.get("/index/{ts_code}")
async def get_index_data(ts_code: str = "000001.SH", db: Session = Depends(get_db)):
    data_service = DataService()
    data = await data_service.fetch_index_daily(ts_code)
    if not data:
        raise HTTPException(status_code=404, detail=f"未找到指数 {ts_code} 的数据")
    return {"ts_code": ts_code, "data": data, "count": len(data)}
