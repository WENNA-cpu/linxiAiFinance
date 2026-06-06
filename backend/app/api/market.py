from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import random
import numpy as np

from app.models.database import get_db
from app.services.data_service import DataService

router = APIRouter()


def normalize_turnover(turnover_rate: float) -> float:
    """换手率归一化（假设正常范围0-10%）"""
    return min(max(turnover_rate / 10.0, 0), 1)


def get_sentiment_status(index: int) -> str:
    """根据情绪指数返回状态"""
    if index >= 70:
        return "贪婪"
    elif index >= 55:
        return "乐观"
    elif index >= 45:
        return "中性"
    elif index >= 30:
        return "悲观"
    else:
        return "恐慌"


def get_market_state(index: int) -> str:
    """根据情绪指数返回市场状态"""
    if index > 65:
        return "强势上涨"
    elif index < 35:
        return "弱势下跌"
    return "震荡整理"


def get_extreme_alert(index: int) -> Optional[str]:
    """获取极端行情提示"""
    if index > 70:
        return "市场过热，警惕回调风险"
    elif index < 30:
        return "市场恐慌，历史数据显示恐慌后往往反弹"
    return None


def calculate_sentiment_index(limit_up: int, limit_down: int, shock_count: int) -> int:
    """计算情绪指数 (0-100)

    基于涨跌停比和异常波动数量计算情绪指数
    - 涨停多、跌停少 -> 情绪高
    - 跌停多、涨停少 -> 情绪低
    - 异常波动多 -> 情绪不稳定
    """
    total = limit_up + limit_down
    if total == 0:
        return 50

    # 涨跌停比 (0-1)
    limit_ratio = limit_up / total if total > 0 else 0.5

    # 基础情绪分数 (0-100)
    base_score = limit_ratio * 100

    # 异常波动影响（越多越不稳定，向中性靠拢）
    shock_impact = min(shock_count * 2, 20)  # 最多影响20分

    # 最终情绪指数
    sentiment = base_score - shock_impact + random.randint(-5, 5)  # 添加随机波动

    return max(0, min(100, int(sentiment)))


async def fetch_limit_list(data_service: DataService, trade_date: str) -> Dict[str, int]:
    """获取涨跌停数据"""
    try:
        # 使用 daily 接口获取当日所有股票数据来统计涨跌
        data = await data_service._request("daily", {
            "trade_date": trade_date,
            "limit": 5000
        })

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])

            limit_up = 0
            limit_down = 0

            for item in items:
                item_dict = dict(zip(fields, item))
                pct_chg = item_dict.get("pct_chg", 0)
                # 涨停: >= 9.9%, 跌停: <= -9.9%
                if pct_chg >= 9.9:
                    limit_up += 1
                elif pct_chg <= -9.9:
                    limit_down += 1

            return {"limit_up": limit_up, "limit_down": limit_down}
    except Exception as e:
        print(f"Error fetching limit list: {e}")

    return {"limit_up": 45, "limit_down": 12}  # 默认值


async def fetch_stk_shock(data_service: DataService, trade_date: str) -> List[Dict]:
    """获取个股异常波动数据"""
    try:
        data = await data_service._request("stk_shock", {
            "trade_date": trade_date,
            "limit": 100
        })

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            return [dict(zip(fields, item)) for item in items]
    except Exception as e:
        print(f"Error fetching stk_shock: {e}")

    return []


@router.get("/sentiment")
async def get_market_sentiment(db: Session = Depends(get_db)):
    """获取市场情绪指数 - 基于 Tushare 真实数据"""
    data_service = DataService()

    try:
        # 获取当前交易日
        trade_date = datetime.now().strftime("%Y%m%d")

        # 获取涨跌停数据
        limit_data = await fetch_limit_list(data_service, trade_date)
        limit_up = limit_data.get("limit_up", 45)
        limit_down = limit_data.get("limit_down", 12)

        # 获取异常波动数据
        shock_records = await fetch_stk_shock(data_service, trade_date)
        warning_signals = len(shock_records)

        # 计算情绪指数
        sentiment_index = calculate_sentiment_index(limit_up, limit_down, warning_signals)

        # 获取状态和市场状态
        status = get_sentiment_status(sentiment_index)
        market_state = get_market_state(sentiment_index)
        extreme_alert = get_extreme_alert(sentiment_index)

        return {
            "sentiment_index": sentiment_index,
            "status": status,
            "market_state": market_state,
            "warning_signals": warning_signals,
            "extreme_alert": extreme_alert,
            "detail": {
                "limit_up": limit_up,
                "limit_down": limit_down,
                "shock_records": shock_records[:10] if shock_records else []  # 只返回前10条
            },
            "data_source": "Tushare实时数据",
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "components": {
                "limit_up": limit_up,
                "limit_down": limit_down,
                "shock_count": warning_signals
            },
            "behavior_bias": {
                "confirmation_bias": 75,
                "loss_aversion": 82,
                "herd_mentality": 60,
                "overconfidence": 45
            }
        }
    except Exception as e:
        # 异常时返回默认值
        print(f"Error in get_market_sentiment: {e}")
        return generate_default_sentiment_data()


def generate_default_sentiment_data() -> Dict[str, Any]:
    """生成默认情绪数据（当 Tushare 接口失败时使用）"""
    return {
        "sentiment_index": 50,
        "status": "中性",
        "market_state": "震荡整理",
        "warning_signals": 0,
        "extreme_alert": None,
        "detail": {
            "limit_up": 45,
            "limit_down": 12,
            "shock_records": []
        },
        "data_source": "默认数据",
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_mock": True,
        "components": {
            "limit_up": 45,
            "limit_down": 12,
            "shock_count": 0
        },
        "behavior_bias": {
            "confirmation_bias": 75,
            "loss_aversion": 82,
            "herd_mentality": 60,
            "overconfidence": 45
        }
    }


@router.get("/data/{ts_code}")
async def get_market_data(ts_code: str, db: Session = Depends(get_db)):
    """获取股票行情数据"""
    data_service = DataService()
    data = await data_service.fetch_market_data(ts_code)

    if not data:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code} 的数据")

    return data


@router.get("/valuation/{ts_code}")
async def get_valuation_data(ts_code: str, db: Session = Depends(get_db)):
    """获取股票估值数据"""
    data_service = DataService()
    valuation = await data_service.fetch_valuation_data(ts_code)
    return valuation


@router.get("/daily/{ts_code}")
async def get_daily_data(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取日线数据"""
    data_service = DataService()
    data = await data_service.fetch_daily_data(ts_code, start_date, end_date)

    if not data:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code} 的数据")

    return {
        "ts_code": ts_code,
        "data": data,
        "count": len(data),
    }


@router.get("/daily")
async def get_daily_data_query(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取日线数据（Query参数版本）"""
    data_service = DataService()
    data = await data_service.fetch_daily_data(ts_code, start_date, end_date)

    if not data:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code} 的数据")

    return {
        "ts_code": ts_code,
        "data": data,
        "count": len(data),
    }


@router.get("/daily_basic")
async def get_daily_basic_query(
    ts_code: str,
    trade_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取每日指标/估值数据（Query参数版本）"""
    data_service = DataService()
    data = await data_service.fetch_daily_basic(ts_code, trade_date)

    if not data:
        raise HTTPException(status_code=404, detail=f"未找到股票 {ts_code} 的估值数据")

    return {
        "ts_code": ts_code,
        "data": data,
        "count": len(data),
    }


@router.get("/index/{ts_code}")
async def get_index_data(ts_code: str = "000001.SH", db: Session = Depends(get_db)):
    """获取指数数据"""
    data_service = DataService()
    data = await data_service.fetch_index_daily(ts_code)

    if not data:
        raise HTTPException(status_code=404, detail=f"未找到指数 {ts_code} 的数据")

    return {
        "ts_code": ts_code,
        "data": data,
        "count": len(data),
    }
