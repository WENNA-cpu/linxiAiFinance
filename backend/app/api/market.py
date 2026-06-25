from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import asyncio
import random
import time

from app.models.database import get_db
from app.services.data_service import DataService
from app.api.tushare_fallback import (
    warn_tushare_mock,
    mock_market_data,
    mock_valuation,
    mock_daily_list,
    mock_index_daily,
)

router = APIRouter()

# 情绪指标短时间内变化小，缓存 8 分钟以减少 Tushare 调用
SENTIMENT_CACHE_TTL = 480
SENTIMENT_FETCH_TIMEOUT = 8
STOCK_META_CACHE_TTL = 600
_sentiment_metrics_cache: Optional[Dict[str, Any]] = None
_sentiment_metrics_cached_at: float = 0.0
_stock_industry_cache: Optional[Dict[str, str]] = None
_stock_industry_cached_at: float = 0.0


class EmotionPortfolioAsset(BaseModel):
    code: str
    name: str = ""
    type: str = "stock"


class EmotionPortfolioInput(BaseModel):
    assets: List[EmotionPortfolioAsset] = []

DATA_SOURCE_LABEL = (
    "数据基于Tushare全市场换手率、涨跌比等公开数据加权计算，仅作参考。"
)


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


async def fetch_limit_list(data_service: DataService, trade_date: str) -> Optional[Dict[str, int]]:
    """拉取涨跌停统计；API 失败返回 None"""
    try:
        data = await data_service._request("daily", {"trade_date": trade_date, "limit": 5000})
        if not data or "items" not in data:
            warn_tushare_mock(f"daily limit_list trade_date={trade_date}")
            return None
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
        warn_tushare_mock(f"fetch_limit_list: {e}")
    return None


async def fetch_stk_shock(data_service: DataService, trade_date: str) -> List[Dict]:
    try:
        data = await data_service._request("stk_shock", {"trade_date": trade_date, "limit": 100})
        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            return [dict(zip(fields, item)) for item in items]
        warn_tushare_mock(f"stk_shock trade_date={trade_date}")
    except Exception as e:
        warn_tushare_mock(f"fetch_stk_shock: {e}")
    return []


def _normalize_ts_code(code: str) -> str:
    trimmed = code.strip().upper()
    if "." in trimmed:
        return trimmed
    if trimmed.startswith(("6", "5")):
        return f"{trimmed}.SH"
    return f"{trimmed}.SZ"


def _bare_code(code: str) -> str:
    return _normalize_ts_code(code).split(".")[0]


async def _get_stock_industry_map(data_service: DataService) -> Dict[str, str]:
    global _stock_industry_cache, _stock_industry_cached_at
    now = time.time()
    if _stock_industry_cache is not None and now - _stock_industry_cached_at < STOCK_META_CACHE_TTL:
        return _stock_industry_cache

    industry_map: Dict[str, str] = {}
    try:
        stock_basic = await data_service.fetch_stock_basic()
        if stock_basic:
            for row in stock_basic:
                ts_code = str(row.get("ts_code") or "")
                industry = str(row.get("industry") or "").strip() or "综合"
                if ts_code:
                    industry_map[ts_code] = industry
                    industry_map[_bare_code(ts_code)] = industry
    except Exception as e:
        warn_tushare_mock(f"fetch_stock_basic: {e}")

    _stock_industry_cache = industry_map
    _stock_industry_cached_at = now
    return industry_map


def _resolve_asset_industry(asset: EmotionPortfolioAsset, industry_map: Dict[str, str]) -> str:
    if asset.type == "fund":
        return "基金"
    if asset.type == "bond":
        return "债券"
    if asset.type == "other":
        return "其他"

    ts_code = _normalize_ts_code(asset.code)
    bare = _bare_code(asset.code)
    return industry_map.get(ts_code) or industry_map.get(bare) or "综合"


def _mock_emotion_portfolio_context(assets: List[EmotionPortfolioAsset]) -> Dict[str, Any]:
    return {
        "asset_industries": [
            {
                "code": asset.code,
                "name": asset.name,
                "type": asset.type,
                "industry": _resolve_asset_industry(asset, {}),
            }
            for asset in assets
        ],
        "data_source": "Mock 行业分类",
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_mock": True,
    }


def _mock_behavior_bias_response(*, cached: bool = False) -> Dict[str, Any]:
    bias = calculate_behavior_bias(50, 0, 0, 0)
    return {
        **bias,
        "sentiment_index": 50,
        "data_source": DATA_SOURCE_LABEL,
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cached": cached,
        "is_mock": True,
        "methodology": {
            "confirmation_bias": "情绪越高，确认偏误越强",
            "loss_aversion": "情绪越低，损失厌恶越强",
            "herd_mentality": "涨跌停比极端时，羊群效应增强",
            "overconfidence": "市场过热时，过度自信风险上升",
        },
    }


@router.post("/emotion-portfolio-context")
async def get_emotion_portfolio_context(
    data: EmotionPortfolioInput,
    db: Session = Depends(get_db),
):
    """为情绪纠偏页提供 Tushare 行业分类"""
    try:
        data_service = DataService()
        industry_map = await _get_stock_industry_map(data_service)

        asset_industries = [
            {
                "code": asset.code,
                "name": asset.name,
                "type": asset.type,
                "industry": _resolve_asset_industry(asset, industry_map),
            }
            for asset in data.assets
        ]

        return {
            "asset_industries": asset_industries,
            "data_source": "Tushare stock_basic 行业分类",
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        warn_tushare_mock(f"emotion-portfolio-context: {e}")
        return _mock_emotion_portfolio_context(data.assets)


def _get_cached_sentiment_metrics() -> Optional[Dict[str, Any]]:
    global _sentiment_metrics_cache, _sentiment_metrics_cached_at
    if _sentiment_metrics_cache is None:
        return None
    if time.time() - _sentiment_metrics_cached_at >= SENTIMENT_CACHE_TTL:
        return None
    return _sentiment_metrics_cache


def _set_cached_sentiment_metrics(metrics: Dict[str, Any]) -> None:
    global _sentiment_metrics_cache, _sentiment_metrics_cached_at
    _sentiment_metrics_cache = metrics
    _sentiment_metrics_cached_at = time.time()


def _mock_sentiment_response(*, cached: bool = False) -> Dict[str, Any]:
    """Tushare 不可用时的保底数据，确保前端不报错"""
    return {
        "sentiment_index": 50,
        "status": "中性",
        "market_state": "震荡整理",
        "warning_signals": 0,
        "extreme_alert": None,
        "detail": {
            "limit_up": 0,
            "limit_down": 0,
            "shock_records": [],
        },
        "data_source": DATA_SOURCE_LABEL,
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cached": cached,
        "components": {
            "limit_up": 0,
            "limit_down": 0,
            "shock_count": 0,
        },
        "is_mock": True,
    }


def _resolve_trade_date_fast() -> str:
    """本地推算最近交易日，避免 trade_cal 限流导致接口超时"""
    cn_now = DataService._cn_now()
    while cn_now.weekday() >= 5:
        cn_now -= timedelta(days=1)
    return cn_now.strftime("%Y%m%d")


async def _fetch_limit_list_with_fallback(data_service: DataService) -> Optional[tuple[Dict[str, int], str]]:
    """向前回溯若干交易日，直到 daily 接口成功响应"""
    trade_date = _resolve_trade_date_fast()

    for _ in range(6):
        while datetime.strptime(trade_date, "%Y%m%d").weekday() >= 5:
            trade_date = (datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")

        result = await fetch_limit_list(data_service, trade_date)
        if result is not None:
            return result, trade_date

        trade_date = (datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")

    return None


async def _fetch_sentiment_from_tushare() -> Dict[str, Any]:
    """从 Tushare 拉取情绪指标；失败时抛出 Exception"""
    data_service = DataService()
    if not data_service.tushare_token:
        raise RuntimeError("TUSHARE_TOKEN 未配置")

    try:
        limit_bundle = await asyncio.wait_for(
            _fetch_limit_list_with_fallback(data_service),
            timeout=6,
        )
        if limit_bundle is None:
            raise RuntimeError("Tushare daily 涨跌停统计无响应")

        limit_data, trade_date = limit_bundle
        limit_up = limit_data.get("limit_up", 0)
        limit_down = limit_data.get("limit_down", 0)

        shock_records = await asyncio.wait_for(
            fetch_stk_shock(data_service, trade_date),
            timeout=3,
        )
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
            "trade_date": trade_date,
        }
    except asyncio.TimeoutError as exc:
        warn_tushare_mock("sentiment Tushare 请求超时")
        raise RuntimeError("Tushare 请求超时") from exc
    except Exception as exc:
        warn_tushare_mock(f"sentiment Tushare: {exc}")
        raise


async def _fetch_sentiment_metrics(*, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    if use_cache:
        cached = _get_cached_sentiment_metrics()
        if cached is not None:
            return cached

    try:
        metrics = await asyncio.wait_for(
            _fetch_sentiment_from_tushare(),
            timeout=SENTIMENT_FETCH_TIMEOUT,
        )
    except Exception as e:
        warn_tushare_mock(f"_fetch_sentiment_metrics: {e}")
        return None

    _set_cached_sentiment_metrics(metrics)
    return metrics


def _build_sentiment_response(metrics: Dict[str, Any], *, cached: bool = False) -> Dict[str, Any]:
    return {
        "sentiment_index": metrics["sentiment_index"],
        "status": metrics["status"],
        "market_state": metrics["market_state"],
        "warning_signals": metrics["warning_signals"],
        "extreme_alert": metrics.get("extreme_alert"),
        "detail": {
            "limit_up": metrics.get("limit_up", 0),
            "limit_down": metrics.get("limit_down", 0),
            "shock_records": (metrics.get("shock_records") or [])[:10],
        },
        "data_source": DATA_SOURCE_LABEL,
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cached": cached,
        "components": {
            "limit_up": metrics.get("limit_up", 0),
            "limit_down": metrics.get("limit_down", 0),
            "shock_count": metrics.get("shock_count", 0),
        },
    }


@router.get("/sentiment")
async def get_market_sentiment(db: Session = Depends(get_db)):
    """获取市场情绪指数 - 基于 Tushare 真实数据，失败时 Mock 保底"""
    cached_metrics = _get_cached_sentiment_metrics()
    if cached_metrics is not None:
        return _build_sentiment_response(cached_metrics, cached=True)

    try:
        metrics = await asyncio.wait_for(
            _fetch_sentiment_from_tushare(),
            timeout=SENTIMENT_FETCH_TIMEOUT,
        )
        _set_cached_sentiment_metrics(metrics)
        return _build_sentiment_response(metrics, cached=False)
    except Exception as e:
        warn_tushare_mock(f"sentiment: {e}")
        return _mock_sentiment_response()


@router.get("/behavior-bias")
async def get_behavior_bias(db: Session = Depends(get_db)):
    """获取行为偏差检测数据 - 基于市场情绪计算"""
    try:
        was_cached = _get_cached_sentiment_metrics() is not None
        metrics = await _fetch_sentiment_metrics()
        if metrics is None:
            warn_tushare_mock("behavior-bias metrics unavailable")
            return _mock_behavior_bias_response(cached=was_cached)
        bias = calculate_behavior_bias(
            metrics["sentiment_index"],
            metrics.get("limit_up", 0),
            metrics.get("limit_down", 0),
            metrics.get("shock_count", 0),
        )
        return {
            **bias,
            "sentiment_index": metrics["sentiment_index"],
            "data_source": DATA_SOURCE_LABEL,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cached": was_cached,
            "methodology": {
                "confirmation_bias": "情绪越高，确认偏误越强",
                "loss_aversion": "情绪越低，损失厌恶越强",
                "herd_mentality": "涨跌停比极端时，羊群效应增强",
                "overconfidence": "市场过热时，过度自信风险上升",
            },
        }
    except Exception as e:
        warn_tushare_mock(f"behavior-bias: {e}")
        return _mock_behavior_bias_response()


@router.get("/data/{ts_code}")
async def get_market_data(ts_code: str, db: Session = Depends(get_db)):
    try:
        data_service = DataService()
        data = await data_service.fetch_market_data(ts_code)
        if data:
            return data
        warn_tushare_mock(f"market_data empty {ts_code}")
        return mock_market_data(ts_code)
    except Exception as e:
        warn_tushare_mock(f"market_data {ts_code}: {e}")
        return mock_market_data(ts_code)


@router.get("/valuation/{ts_code}")
async def get_valuation_data(ts_code: str, db: Session = Depends(get_db)):
    try:
        data_service = DataService()
        valuation = await data_service.fetch_valuation_data(ts_code)
        if valuation:
            return valuation
        warn_tushare_mock(f"valuation empty {ts_code}")
        return mock_valuation(ts_code)
    except Exception as e:
        warn_tushare_mock(f"valuation {ts_code}: {e}")
        return mock_valuation(ts_code)


@router.get("/daily/{ts_code}")
async def get_daily_data(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        data_service = DataService()
        data = await data_service.fetch_daily_data(ts_code, start_date, end_date)
        if data:
            return {"ts_code": ts_code, "data": data, "count": len(data)}
        warn_tushare_mock(f"daily empty {ts_code}")
        mock_data = mock_daily_list(ts_code)
        return {"ts_code": ts_code, "data": mock_data, "count": len(mock_data), "is_mock": True}
    except Exception as e:
        warn_tushare_mock(f"daily {ts_code}: {e}")
        mock_data = mock_daily_list(ts_code)
        return {"ts_code": ts_code, "data": mock_data, "count": len(mock_data), "is_mock": True}


@router.get("/daily")
async def get_daily_data_query(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return await get_daily_data(ts_code, start_date, end_date, db)


@router.get("/daily_basic")
async def get_daily_basic_query(
    ts_code: str,
    trade_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        data_service = DataService()
        data = await data_service.fetch_daily_basic(ts_code, trade_date)
        if data:
            return {"ts_code": ts_code, "data": data, "count": len(data)}
        warn_tushare_mock(f"daily_basic empty {ts_code}")
        mock_row = mock_valuation(ts_code)
        return {"ts_code": ts_code, "data": [mock_row], "count": 1, "is_mock": True}
    except Exception as e:
        warn_tushare_mock(f"daily_basic {ts_code}: {e}")
        mock_row = mock_valuation(ts_code)
        return {"ts_code": ts_code, "data": [mock_row], "count": 1, "is_mock": True}


@router.get("/index/{ts_code}")
async def get_index_data(ts_code: str = "000001.SH", db: Session = Depends(get_db)):
    try:
        data_service = DataService()
        data = await data_service.fetch_index_daily(ts_code)
        if data:
            return {"ts_code": ts_code, "data": data, "count": len(data)}
        warn_tushare_mock(f"index empty {ts_code}")
        mock_data = mock_index_daily(ts_code)
        return {"ts_code": ts_code, "data": mock_data, "count": len(mock_data), "is_mock": True}
    except Exception as e:
        warn_tushare_mock(f"index {ts_code}: {e}")
        mock_data = mock_index_daily(ts_code)
        return {"ts_code": ts_code, "data": mock_data, "count": len(mock_data), "is_mock": True}
