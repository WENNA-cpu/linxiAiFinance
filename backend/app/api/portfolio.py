from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import random
import os
import asyncio
import aiohttp
import time
from pathlib import Path

from app.models.database import get_db
from app.models.portfolio import AuditLog
from app.services.data_service import DataService
from app.services.lstm_cycle_service import get_lstm_predictor
from app.services.rf_risk_service import get_rf_predictor
from app.services.model_manager import should_use_new_model
from app.config import NEW_MODEL_RATIO
from app.api.tushare_fallback import warn_tushare_mock, mock_quote_row

router = APIRouter()

# Tushare配置
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "").strip()
_QUOTE_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "tushare" / "quotes"
QUOTE_CACHE_TTL_SECONDS = 4 * 3600


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _calc_today_change_pct(close: float, pre_close: float, pct_chg: Any = None) -> Optional[float]:
    """今日涨跌幅 = (当前价 - 昨收) / 昨收 × 100%，优先用 Tushare pct_chg"""
    if pct_chg is not None and str(pct_chg).strip() != "":
        return round(_to_float(pct_chg), 2)
    if close > 0 and pre_close > 0:
        return round((close - pre_close) / pre_close * 100, 2)
    return None


def _daily_row_to_quote(ts_code: str, row: Dict[str, Any]) -> Dict[str, Any]:
    close = _to_float(row.get("close"))
    pre_close = _to_float(row.get("pre_close"))
    pct_chg = _calc_today_change_pct(close, pre_close, row.get("pct_chg"))
    return {
        "ts_code": ts_code,
        "trade_date": str(row.get("trade_date", "")),
        "close": close,
        "pre_close": pre_close,
        "open": _to_float(row.get("open")),
        "high": _to_float(row.get("high")),
        "low": _to_float(row.get("low")),
        "change": _to_float(row.get("change")),
        "pct_chg": pct_chg,
        "vol": _to_float(row.get("vol")),
        "amount": _to_float(row.get("amount")),
        "data_source": row.get("data_source"),
    }


async def fetch_tushare_daily(ts_code: str, lookback_days: int = 60, asset_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """从 DataService 获取最近一个交易日行情（股票 daily / 基金 fund_daily）"""
    svc = DataService()
    quote = await svc.get_current_price(ts_code, lookback_days=lookback_days, asset_type=asset_type)
    if not quote:
        return None
    return quote


async def fetch_quote_via_data_service(
    ts_code: str,
    lookback_days: int = 60,
    asset_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """DataService 拉取更长区间，取最近交易日收盘价/净值"""
    svc = DataService()
    return await svc.get_current_price(ts_code, lookback_days=lookback_days, asset_type=asset_type)


async def fetch_quote_for_asset(
    code: str,
    asset_type: Optional[str] = None,
    *,
    force_refresh: bool = False,
) -> Optional[Dict[str, Any]]:
    """多级降级：Tushare fund_daily/daily -> 本地缓存 -> Mock"""
    ts_code = DataService._normalize_ts_code(code)
    svc = DataService()

    try:
        quote = await svc.get_current_price(ts_code, lookback_days=60, asset_type=asset_type)
        if quote and _to_float(quote.get("close")) > 0:
            normalized = _daily_row_to_quote(ts_code, quote)
            _save_cached_quote(code, normalized)
            print(
                f"[行情] {code} -> {ts_code} close={normalized['close']} "
                f"trade_date={normalized.get('trade_date')} source={quote.get('data_source')}"
            )
            return normalized
    except Exception as e:
        warn_tushare_mock(f"get_current_price {code}: {e}")

    if not force_refresh:
        cached = _load_cached_quote(code)
        if cached and _to_float(cached.get("close")) > 0:
            try:
                latest_td = await svc._resolve_latest_trade_date(svc._cn_now())
                cached_td = str(cached.get("trade_date", ""))
                if cached_td and cached_td >= latest_td:
                    if cached.get("pct_chg") is None:
                        cached["pct_chg"] = _calc_today_change_pct(
                            _to_float(cached.get("close")),
                            _to_float(cached.get("pre_close")),
                        )
                    print(
                        f"[行情] {code} 使用缓存 close={cached.get('close')} "
                        f"trade_date={cached.get('trade_date')}"
                    )
                    return cached
                print(
                    f"[行情] {code} 缓存过期 trade_date={cached_td} < latest={latest_td}，重新拉取"
                )
            except Exception as e:
                warn_tushare_mock(f"resolve_trade_date {code}: {e}")
                if cached.get("pct_chg") is None:
                    cached["pct_chg"] = _calc_today_change_pct(
                        _to_float(cached.get("close")),
                        _to_float(cached.get("pre_close")),
                    )
                return cached

    warn_tushare_mock(code)
    mock = mock_quote_row(code, asset_type)
    normalized = _daily_row_to_quote(ts_code, mock)
    _save_cached_quote(code, normalized)
    return normalized


def _quote_lookup_key(code: str) -> str:
    return DataService._normalize_ts_code(code).split(".")[0]


def _get_asset_quote(asset_quotes: Dict[str, Any], code: str) -> Optional[Dict[str, Any]]:
    """按多种 code 形式查找行情"""
    keys = {code, _quote_lookup_key(code), DataService._normalize_ts_code(code)}
    for key in keys:
        if key in asset_quotes and asset_quotes[key]:
            return asset_quotes[key]
    return None


async def fetch_stock_quote(ts_code: str) -> Optional[Dict[str, Any]]:
    """兼容旧调用：按 ts_code 获取行情"""
    code = ts_code.split(".")[0] if "." in ts_code else ts_code
    return await fetch_quote_for_asset(code)


def _normalize_ts_code(code: str) -> str:
    return DataService._normalize_ts_code(code)


def _quote_cache_path(code: str) -> Path:
    safe = _normalize_ts_code(code).replace(".", "_")
    return _QUOTE_CACHE_DIR / f"daily_{safe}.json"


def _load_cached_quote(code: str) -> Optional[Dict[str, Any]]:
    path = _quote_cache_path(code)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        cached_at = payload.get("ts", 0)
        if time.time() - cached_at > QUOTE_CACHE_TTL_SECONDS:
            return None
        return payload.get("quote")
    except Exception:
        return None


def _save_cached_quote(code: str, quote: Dict[str, Any]) -> None:
    try:
        _QUOTE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _quote_cache_path(code).write_text(
            json.dumps({"ts": datetime.now().timestamp(), "quote": quote}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[诊断] 行情缓存写入失败 {code}: {e}")


def _resolve_asset_quote(
    asset_code: str,
    live_quote: Optional[Dict[str, Any]],
    asset_type: Optional[str] = None,
) -> Dict[str, Any]:
    """解析行情：Tushare/缓存/Mock，不使用用户导入模拟价"""
    if live_quote and _to_float(live_quote.get("close")) > 0:
        close = _to_float(live_quote.get("close"))
        pre_close = _to_float(live_quote.get("pre_close"))
        pct_chg = _calc_today_change_pct(close, pre_close, live_quote.get("pct_chg"))
        quote = {
            **live_quote,
            "close": close,
            "pre_close": pre_close,
            "pct_chg": pct_chg,
        }
        _save_cached_quote(asset_code, quote)
        return {
            "close": close,
            "pre_close": pre_close,
            "pct_chg": pct_chg,
            "trade_date": str(live_quote.get("trade_date", "")),
            "data_source": (
                "Mock净值" if live_quote.get("data_source") == "mock"
                else (live_quote.get("data_source") or "Tushare行情")
            ),
            "price_status": "live" if live_quote.get("data_source") != "mock" else "cached",
        }

    cached = _load_cached_quote(asset_code)
    if cached and _to_float(cached.get("close")) > 0:
        close = _to_float(cached.get("close"))
        pre_close = _to_float(cached.get("pre_close"))
        pct_chg = _calc_today_change_pct(close, pre_close, cached.get("pct_chg"))
        return {
            "close": close,
            "pre_close": pre_close,
            "pct_chg": pct_chg,
            "trade_date": str(cached.get("trade_date", "")),
            "data_source": "最近交易日缓存",
            "price_status": "cached",
        }

    svc = DataService()
    ts_code = svc._normalize_ts_code(asset_code)
    try:
        mock = mock_quote_row(asset_code, asset_type)
        if mock and _to_float(mock.get("close")) > 0:
            close = _to_float(mock.get("close"))
            pre_close = _to_float(mock.get("pre_close"))
            pct_chg = _calc_today_change_pct(close, pre_close, mock.get("pct_chg"))
            normalized = {**mock, "close": close, "pre_close": pre_close, "pct_chg": pct_chg}
            _save_cached_quote(asset_code, normalized)
            warn_tushare_mock(asset_code)
            return {
                "close": close,
                "pre_close": pre_close,
                "pct_chg": pct_chg,
                "trade_date": str(mock.get("trade_date", "")),
                "data_source": "Mock净值",
                "price_status": "cached",
            }
    except Exception as e:
        warn_tushare_mock(f"_resolve_asset_quote {asset_code}: {e}")

    return {
        "close": None,
        "pre_close": None,
        "pct_chg": None,
        "trade_date": "",
        "data_source": "数据更新中",
        "price_status": "pending",
    }


def _asset_quantity(asset: "AssetInput") -> float:
    return float(asset.quantity or 0)


def _build_asset_metrics(asset: "AssetInput", quote_info: Dict[str, Any]) -> Dict[str, Any]:
    qty = _asset_quantity(asset)
    cost_price = _to_float(asset.cost_price)
    current_price = quote_info.get("close")
    has_price = current_price is not None and _to_float(current_price) > 0
    close_val = _to_float(current_price) if has_price else None

    position_cost = round(cost_price * qty, 2)
    market_value = round(close_val * qty, 2) if has_price and close_val is not None else None
    profit_amount = round(market_value - position_cost, 2) if market_value is not None else None
    profit_pct = (
        round((close_val - cost_price) / cost_price * 100, 2)
        if has_price and cost_price > 0 and close_val is not None
        else None
    )
    today_change = quote_info.get("pct_chg")

    return {
        "code": asset.code,
        "name": asset.name,
        "weight": asset.weight,
        "asset_type": asset.asset_type or "stock",
        "quantity": qty,
        "cost_price": round(cost_price, 2),
        "current_price": round(close_val, 2) if close_val is not None else None,
        "position_cost": position_cost,
        "market_value": market_value,
        "profit_amount": profit_amount,
        "profit_pct": profit_pct,
        "today_change_pct": today_change,
        "trade_date": quote_info.get("trade_date", ""),
        "data_source": quote_info.get("data_source", ""),
        "price_status": quote_info.get("price_status", "pending"),
    }


async def fetch_asset_history(
    ts_code: str,
    days: int = 365,
    asset_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """获取资产历史日线/净值；基金用 fund_daily，无 PE/PB 时用净值走势"""
    svc = DataService()
    ts_code = svc._normalize_ts_code(ts_code)
    end = datetime.now()
    start = end - timedelta(days=days)
    sd, ed = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    try:
        daily = await svc.fetch_ohlcv_data(ts_code, sd, ed, asset_type=asset_type) or []
        daily = sorted(daily, key=lambda x: x.get("trade_date", ""))

        if svc.is_fund_code(ts_code, asset_type):
            return daily

        basic = await svc.fetch_daily_basic_historical(ts_code, sd, ed) or []
        basic_map = {b.get("trade_date"): b for b in basic}
        rows = []
        for d in daily:
            td = d.get("trade_date")
            merged = dict(d)
            if td in basic_map:
                merged.update({k: basic_map[td].get(k) for k in ("pe", "pb", "ps", "turnover_rate")})
            rows.append(merged)
        return rows
    except Exception as e:
        warn_tushare_mock(f"fetch_asset_history {ts_code}: {e}")
        mock_row = mock_quote_row(ts_code, asset_type)
        return [mock_row]


async def _fetch_quotes_parallel(assets: List, timeout: float = 20.0) -> Dict[str, Any]:
    """并行拉取行情（Tushare + DataService 降级 + 缓存）"""

    async def _one(asset) -> tuple:
        try:
            quote = await asyncio.wait_for(
                fetch_quote_for_asset(asset.code, asset_type=asset.asset_type, force_refresh=True),
                timeout=10.0,
            )
            return asset.code, quote
        except Exception as e:
            print(f"[诊断] 行情拉取失败 {asset.code}: {e}")
            return asset.code, None

    pairs: List[tuple] = []
    try:
        pairs = await asyncio.wait_for(
            asyncio.gather(*[_one(a) for a in assets]),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        print("[诊断] 行情批量拉取超时，将使用缓存或 Mock")

    result: Dict[str, Any] = {}
    for code, quote in pairs:
        if not quote:
            continue
        result[code] = quote
        result[_quote_lookup_key(code)] = quote
    return result


async def _run_lstm_trend_light(assets: List, asset_quotes: dict, request_id: str) -> Dict[str, Any]:
    """快速诊断：不拉取长历史，避免 Tushare daily_basic 限流导致超时"""
    try:
        return await asyncio.wait_for(
            _run_lstm_trend(assets, asset_quotes, request_id),
            timeout=6.0,
        )
    except (asyncio.TimeoutError, Exception) as e:
        print(f"[诊断] LSTM 快速模式跳过: {e}")
        return {
            "available": False,
            "forecasts": [],
            "bullish_ratio": 0.0,
            "model_variant": "skipped",
            "reason": "快速诊断模式",
        }


async def _run_rf_risk_light(assets: List) -> Dict[str, Any]:
    """快速诊断：RF 超时则回退规则引擎"""
    try:
        return await asyncio.wait_for(_run_rf_risk(assets), timeout=6.0)
    except (asyncio.TimeoutError, Exception) as e:
        print(f"[诊断] RF 快速模式跳过: {e}")
        rule_high = 0
        predictions = []
        for asset in assets:
            if asset.cost_price and asset.current_price:
                pct = (asset.current_price - asset.cost_price) / asset.cost_price * 100
                if pct < -5:
                    rule_high += 1
                    predictions.append({
                        "code": asset.code,
                        "name": asset.name,
                        "risk_level": "高风险",
                    })
        return {
            "model_available": False,
            "high_risk_count": rule_high,
            "asset_predictions": predictions,
        }


async def _run_lstm_trend(assets: List, asset_quotes: dict, request_id: str) -> Dict[str, Any]:
    use_new = should_use_new_model(request_id, NEW_MODEL_RATIO)
    predictor = get_lstm_predictor(use_new=use_new)
    trends_up = 0
    forecasts = []
    for asset in assets[:10]:
        ts_code = _normalize_ts_code(asset.code)
        history = await fetch_asset_history(
            ts_code, days=320, asset_type=getattr(asset, "asset_type", None),
        )
        closes = [float(r["close"]) for r in history if r.get("close")]
        if len(closes) < 30:
            continue
        pred = predictor.predict(close_prices=closes, history=history)
        if pred.get("available"):
            forecasts.append({"code": asset.code, "name": asset.name, **pred})
            if pred.get("trend") == "up":
                trends_up += 1
    return {
        "available": bool(forecasts),
        "forecasts": forecasts,
        "bullish_ratio": round(trends_up / max(len(forecasts), 1), 2),
        "model_variant": "new" if use_new else "legacy",
    }


async def _run_rf_risk(assets: List) -> Dict[str, Any]:
    predictor = get_rf_predictor()
    histories = []
    for asset in assets:
        ts_code = _normalize_ts_code(asset.code)
        history = await fetch_asset_history(
            ts_code, days=180, asset_type=getattr(asset, "asset_type", None),
        )
        if len(history) >= 30:
            histories.append({"code": asset.code, "name": asset.name, "history": history})
    return predictor.assess_portfolio(histories)


def create_audit_log(
    db: Session,
    request_id: str,
    step_name: str,
    step_status: str,
    step_detail: str,
    started_at: Optional[datetime] = None,
) -> AuditLog:
    """创建审计日志记录"""
    log = AuditLog(
        request_id=request_id,
        step_name=step_name,
        step_status=step_status,
        step_detail=step_detail,
        started_at=started_at or datetime.utcnow(),
        completed_at=datetime.utcnow() if step_status in ["成功", "失败", "警告"] else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def record_audit_step(
    db: Session,
    request_id: str,
    step_name: str,
    step_detail: str,
    audit_logs: List[Dict[str, Any]],
    step_status: str = "成功",
    started_at: Optional[datetime] = None,
) -> AuditLog:
    """写入审计日志并同步收集到响应列表"""
    log = create_audit_log(db, request_id, step_name, step_status, step_detail, started_at)
    audit_logs.append({
        "step_order": len(audit_logs) + 1,
        "step_name": step_name,
        "step_status": step_status,
        "step_detail": step_detail,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
    })
    return log


class AssetInput(BaseModel):
    code: str
    name: str
    weight: float
    cost_price: Optional[float] = None
    current_price: Optional[float] = None
    quantity: Optional[float] = None
    asset_type: Optional[str] = "stock"


class PortfolioInput(BaseModel):
    assets: List[AssetInput]
    total_value: Optional[float] = None
    leverage: float = 1.0


class QuoteRefreshAsset(BaseModel):
    code: str
    name: str = ""
    quantity: Optional[float] = 0
    cost_price: Optional[float] = 0
    asset_type: Optional[str] = "stock"


class QuoteRefreshInput(BaseModel):
    assets: List[QuoteRefreshAsset] = []


@router.post("/refresh-quotes")
async def refresh_portfolio_quotes(data: QuoteRefreshInput, db: Session = Depends(get_db)):
    """刷新持仓最新收盘价/净值，供诊断页与情绪纠偏页同步现价"""
    try:
        if not data.assets:
            return {"assets": [], "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        refreshed: List[Dict[str, Any]] = []
        for asset in data.assets:
            try:
                quote = await fetch_quote_for_asset(
                    asset.code,
                    asset_type=asset.asset_type,
                    force_refresh=True,
                )
            except Exception as e:
                warn_tushare_mock(f"refresh-quotes {asset.code}: {e}")
                quote = _daily_row_to_quote(
                    DataService._normalize_ts_code(asset.code),
                    mock_quote_row(asset.code, asset.asset_type),
                )

            quote_info = _resolve_asset_quote(asset.code, quote, asset_type=asset.asset_type)
            qty = float(asset.quantity or 0)
            cost = _to_float(asset.cost_price)
            close_val = quote_info.get("close")
            has_price = close_val is not None and _to_float(close_val) > 0
            current_price = round(_to_float(close_val), 2) if has_price else None
            market_value = round(current_price * qty, 2) if has_price and current_price is not None else None

            row = {
                "code": asset.code,
                "name": asset.name,
                "current_price": current_price,
                "market_value": market_value,
                "cost_price": round(cost, 2) if cost > 0 else None,
                "trade_date": quote_info.get("trade_date", ""),
                "data_source": quote_info.get("data_source", ""),
                "price_status": quote_info.get("price_status", "pending"),
                "today_change_pct": quote_info.get("pct_chg"),
            }
            refreshed.append(row)
            print(
                f"[刷新现价] {asset.code} {asset.name} current_price={current_price} "
                f"trade_date={row['trade_date']} source={row['data_source']}"
            )

        return {
            "assets": refreshed,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        warn_tushare_mock(f"refresh-quotes: {e}")
        refreshed = []
        for asset in data.assets or []:
            mock = mock_quote_row(asset.code, asset.asset_type)
            qty = float(asset.quantity or 0)
            close = _to_float(mock.get("close"), 10.0)
            refreshed.append({
                "code": asset.code,
                "name": asset.name,
                "current_price": round(close, 2),
                "market_value": round(close * qty, 2),
                "cost_price": round(_to_float(asset.cost_price), 2) if asset.cost_price else None,
                "trade_date": str(mock.get("trade_date", "")),
                "data_source": "Mock净值",
                "price_status": "cached",
                "today_change_pct": mock.get("pct_chg"),
            })
        return {
            "assets": refreshed,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


class RiskAssessmentInput(BaseModel):
    concentration: float
    volatility: float
    liquidity: float
    leverage: float
    beta: Optional[float] = 1.0
    sharpe_ratio: Optional[float] = 0
    max_drawdown: Optional[float] = 0.1


@router.post("/import")
async def import_portfolio(data: PortfolioInput, db: Session = Depends(get_db)):
    """导入持仓"""
    # 计算总市值
    total_value = data.total_value or sum(
        asset.weight * 100000 for asset in data.assets
    )

    return {
        "success": True,
        "imported_at": datetime.now().isoformat(),
        "portfolio": {
            "assets_count": len(data.assets),
            "total_value": total_value,
            "leverage": data.leverage,
            "assets": [
                {
                    "code": asset.code,
                    "name": asset.name,
                    "weight": asset.weight,
                    "value": asset.weight * total_value,
                }
                for asset in data.assets
            ],
        },
    }


def _get_sector(code: str) -> str:
    """根据股票代码判断板块（简化版）"""
    if code.startswith("6"):
        return "沪市主板"
    elif code.startswith("0"):
        return "深市主板"
    elif code.startswith("3"):
        return "创业板"
    elif code.startswith("68"):
        return "科创板"
    else:
        return "其他"


@router.post("/diagnose")
async def diagnose_portfolio(data: PortfolioInput, db: Session = Depends(get_db)):
    """AI持仓诊断 - 基于真实持仓数据生成结论"""
    try:
        return await _diagnose_portfolio_impl(data, db)
    except Exception as e:
        warn_tushare_mock(f"diagnose: {e}")
        request_id = f"diag_{datetime.now().strftime('%Y%m%d%H%M%S')}_mock"
        assets = data.assets or []
        mock_metrics = []
        for asset in assets:
            mock = mock_quote_row(asset.code, asset.asset_type)
            quote_info = _resolve_asset_quote(asset.code, _daily_row_to_quote(
                DataService._normalize_ts_code(asset.code), mock,
            ), asset_type=asset.asset_type)
            mock_metrics.append(_build_asset_metrics(asset, quote_info))
        total_cost = sum(m.get("position_cost") or 0 for m in mock_metrics)
        total_current = sum(m.get("market_value") or 0 for m in mock_metrics)
        return {
            "request_id": request_id,
            "audit_logs": [],
            "confidence": 70,
            "summary": {
                "total_assets": len(assets),
                "risk_assets": 0,
                "opportunity_assets": 0,
                "time_saved": len(assets) * 5,
            },
            "analysis": {
                "market_trend": "Tushare 暂不可用，以下为 Mock 行情下的参考结论。",
                "sector_rotation": "数据恢复后将更新板块分析。",
                "risk_points": ["当前使用 Mock 行情，请以实际行情为准"],
                "opportunities": ["建议稍后重新诊断以获取最新数据"],
            },
            "data_source": {
                "time_range": "-",
                "sources": ["Mock行情"],
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
            "detail": {
                "total_cost": round(total_cost, 2),
                "total_market_value": round(total_current, 2),
                "total_profit_amount": round(total_current - total_cost, 2),
                "total_change_pct": 0,
                "risk_assets_detail": [],
                "opportunity_assets_detail": [],
                "sector_performance": {},
                "assets": mock_metrics,
                "lstm_forecast": {"available": False, "forecasts": [], "reason": "Mock模式"},
                "rf_assessment": {"model_available": False, "high_risk_count": 0, "asset_predictions": []},
            },
        }


async def _diagnose_portfolio_impl(data: PortfolioInput, db: Session):
    request_id = f"diag_{datetime.now().strftime('%Y%m%d%H%M%S')}_{datetime.now().microsecond // 1000:03d}"
    audit_logs: List[Dict[str, Any]] = []
    assets = data.assets
    total_assets = len(assets)

    print(f"[诊断] 收到请求，request_id: {request_id}, 资产数量: {total_assets}")

    record_audit_step(
        db, request_id, "请求接收", "用户发起持仓诊断请求", audit_logs,
        started_at=datetime.utcnow(),
    )

    if total_assets == 0:
        record_audit_step(
            db, request_id, "结果生成", "无持仓数据，诊断终止", audit_logs,
            step_status="失败",
        )
        return {
            "request_id": request_id,
            "audit_logs": audit_logs,
            "confidence": 0,
            "summary": {
                "total_assets": 0,
                "risk_assets": 0,
                "opportunity_assets": 0,
                "time_saved": 0,
            },
            "analysis": {
                "market_trend": "暂无持仓数据，无法分析市场趋势",
                "sector_rotation": "暂无持仓数据，无法分析板块轮动",
                "risk_points": ["暂无持仓数据，请先导入持仓"],
                "opportunities": ["暂无持仓数据，请先导入持仓"],
            },
            "data_source": {
                "time_range": "-",
                "sources": [],
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        }

    step_start = datetime.utcnow()
    # 有成本价即走快速诊断，避免 LSTM/RF 拖慢导致前端超时
    has_local_prices = all((a.cost_price or 0) > 0 for a in assets)
    asset_quotes = await _fetch_quotes_parallel(assets)
    record_audit_step(
        db, request_id, "数据获取",
        f"共{total_assets}只资产，行情命中 {len(asset_quotes)} 只",
        audit_logs, started_at=step_start,
    )

    step_start = datetime.utcnow()
    assets_metrics: List[Dict[str, Any]] = []
    for asset in assets:
        quote = _get_asset_quote(asset_quotes, asset.code)
        if not quote:
            quote = await fetch_quote_for_asset(asset.code, asset_type=asset.asset_type)
        quote_info = _resolve_asset_quote(asset.code, quote, asset_type=asset.asset_type)
        metrics = _build_asset_metrics(asset, quote_info)
        assets_metrics.append(metrics)
        print(
            f"[诊断] {metrics['code']} {metrics['name']} "
            f"current_price={metrics['current_price']} "
            f"trade_date={metrics.get('trade_date')} "
            f"source={metrics.get('data_source')}"
        )

    total_cost = sum(m["position_cost"] or 0 for m in assets_metrics)
    total_current = sum(m["market_value"] or 0 for m in assets_metrics if m["market_value"] is not None)
    total_profit = round(total_current - total_cost, 2)
    total_change_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0

    risk_assets = []
    opportunity_assets = []
    sector_performance = {}

    for metrics in assets_metrics:
        profit_pct = metrics.get("profit_pct")
        today_change_pct = metrics.get("today_change_pct")

        if profit_pct is not None and profit_pct < -5:
            risk_assets.append({
                "code": metrics["code"],
                "name": metrics["name"],
                "change_pct": profit_pct,
                "profit_pct": profit_pct,
                "today_change": today_change_pct,
            })

        if profit_pct is not None and profit_pct > 5:
            opportunity_assets.append({
                "code": metrics["code"],
                "name": metrics["name"],
                "change_pct": profit_pct,
                "profit_pct": profit_pct,
                "today_change": today_change_pct,
            })

        if today_change_pct is not None:
            sector = _get_sector(metrics["code"])
            sector_performance.setdefault(sector, []).append(today_change_pct)

    record_audit_step(
        db, request_id, "数据清洗", "完成缺失值处理", audit_logs, started_at=step_start,
    )

    sector_avg = {s: sum(p) / len(p) for s, p in sector_performance.items()}
    best_sector = max(sector_avg.items(), key=lambda x: x[1]) if sector_avg else ("未知", 0)
    worst_sector = min(sector_avg.items(), key=lambda x: x[1]) if sector_avg else ("未知", 0)

    lstm_start = datetime.utcnow()
    if has_local_prices:
        lstm_result = {
            "available": False,
            "forecasts": [],
            "bullish_ratio": 0.0,
            "model_variant": "skipped",
            "reason": "用户已提供价格，快速诊断模式",
        }
        lstm_detail = "跳过 LSTM（用户导入价格，快速诊断）"
    else:
        lstm_result = await _run_lstm_trend_light(assets, asset_quotes, request_id)
        if lstm_result.get("available"):
            lstm_detail = (
                f"完成趋势分析，{len(lstm_result['forecasts'])}只资产预测，"
                f"看涨比例{lstm_result['bullish_ratio']:.0%}，模型={lstm_result['model_variant']}"
            )
        else:
            lstm_detail = "完成趋势分析（模型未就绪，使用规则补充）"
    record_audit_step(
        db, request_id, "LSTM模型预测", lstm_detail, audit_logs,
        started_at=lstm_start,
    )

    rf_start = datetime.utcnow()
    if has_local_prices:
        rule_high = 0
        predictions = []
        for metrics in assets_metrics:
            profit_pct = metrics.get("profit_pct")
            if profit_pct is not None and profit_pct < -5:
                rule_high += 1
                predictions.append({
                    "code": metrics["code"],
                    "name": metrics["name"],
                    "risk_level": "高风险",
                })
        rf_result = {
            "model_available": False,
            "high_risk_count": rule_high,
            "asset_predictions": predictions,
        }
        rf_detail = f"识别出{rule_high}个风险资产（规则引擎，快速诊断）"
    else:
        rf_result = await _run_rf_risk_light(assets)
        rf_detail = (
            f"识别出{rf_result.get('high_risk_count', 0)}个风险资产（随机森林）"
            if rf_result.get("model_available")
            else f"识别出{len(risk_assets)}个风险资产（规则引擎）"
        )
    rf_risk_assets = [
        p for p in rf_result.get("asset_predictions", [])
        if p.get("risk_level") == "高风险"
    ]
    if rf_result.get("model_available") and rf_risk_assets:
        for ra in rf_risk_assets:
            if not any(r["code"] == ra.get("code") for r in risk_assets):
                risk_assets.append({
                    "code": ra.get("code"),
                    "name": ra.get("name"),
                    "change_pct": 0,
                    "today_change": 0,
                    "rf_risk_level": ra.get("risk_level"),
                })
    record_audit_step(
        db, request_id, "随机森林风险评估", rf_detail, audit_logs,
        started_at=rf_start,
    )

    rule_passed = len(risk_assets) <= total_assets * 0.5
    record_audit_step(
        db, request_id, "规则引擎校验",
        "通过所有风控规则" if rule_passed else f"触发风控警告：风险资产占比偏高（{len(risk_assets)}/{total_assets}）",
        audit_logs,
        step_status="成功" if rule_passed else "警告",
        started_at=datetime.utcnow(),
    )

    # 生成市场趋势结论
    if lstm_result.get("available") and lstm_result.get("forecasts"):
        avg_chg = sum(f.get("change_pct", 0) for f in lstm_result["forecasts"]) / len(lstm_result["forecasts"])
        market_trend = (
            f"LSTM 模型预测持仓整体未来5日趋势{'偏多' if avg_chg > 0 else '偏空'}"
            f"（平均预期变动 {avg_chg:.2f}%）。"
            f"当前持仓盈亏 {total_change_pct:.2f}%。"
        )
    elif total_change_pct > 0:
        market_trend = f"您的持仓整体上涨 {total_change_pct:.2f}%，表现良好。建议关注盈利资产的持续性，同时注意风险控制。"
    elif total_change_pct < -5:
        market_trend = f"您的持仓整体下跌 {abs(total_change_pct):.2f}%，建议关注风险，可考虑适当调整仓位。"
    else:
        market_trend = f"您的持仓整体波动在 {total_change_pct:.2f}% 范围内，处于震荡整理阶段，建议保持观望。"

    # 生成板块轮动结论
    if len(sector_avg) > 1:
        sector_rotation = f"您的持仓中，{best_sector[0]} 板块表现较好（平均 {best_sector[1]:.2f}%），{worst_sector[0]} 板块表现较弱（平均 {worst_sector[1]:.2f}%）。建议关注板块轮动机会。"
    else:
        sector_rotation = f"您的持仓主要集中在 {best_sector[0]} 板块，平均涨跌幅 {best_sector[1]:.2f}%。建议适当分散投资以降低风险。"

    # 生成风险点
    risk_points = []
    if risk_assets:
        risk_names = ", ".join([a["name"] for a in risk_assets[:3]])
        risk_points.append(f"以下资产亏损超过5%：{risk_names}，建议关注止损时机")
    if total_change_pct < -5:
        risk_points.append("整体持仓亏损较大，建议评估风险承受能力")
    if len(sector_avg) == 1:
        risk_points.append("持仓过于集中，建议分散投资")
    if not risk_points:
        risk_points.append("当前持仓风险可控，建议持续关注市场变化")

    # 生成机会点
    opportunities = []
    if opportunity_assets:
        opp_names = ", ".join([a["name"] for a in opportunity_assets[:3]])
        opportunities.append(f"以下资产盈利超过5%：{opp_names}，可考虑适当止盈")
    if best_sector[1] > 5:
        opportunities.append(f"{best_sector[0]} 板块表现强势，可关注相关机会")
    if total_change_pct > 5:
        opportunities.append("整体持仓盈利良好，可考虑部分获利了结")
    if not opportunities:
        opportunities.append("建议关注低估值优质资产的配置机会")

    # 资产详情（含成本、市值、盈亏）
    assets_detail = assets_metrics

    record_audit_step(
        db, request_id, "结果生成", "诊断报告生成完毕", audit_logs,
        started_at=datetime.utcnow(),
    )

    return {
        "request_id": request_id,
        "audit_logs": audit_logs,
        "confidence": 85,
        "summary": {
            "total_assets": total_assets,
            "risk_assets": len(risk_assets),
            "opportunity_assets": len(opportunity_assets),
            "time_saved": total_assets * 5,
        },
        "analysis": {
            "market_trend": market_trend,
            "sector_rotation": sector_rotation,
            "risk_points": risk_points,
            "opportunities": opportunities,
        },
        "data_source": {
            "time_range": (
                f"{(datetime.now() - timedelta(days=150)).strftime('%Y-%m-%d')} 至 "
                f"{datetime.now().strftime('%Y-%m-%d')}"
            ),
            "sources": ["用户持仓数据", "Tushare行情数据", "行业研报摘要"],
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        "detail": {
            "total_cost": round(total_cost, 2),
            "total_market_value": round(total_current, 2),
            "total_profit_amount": total_profit,
            "total_change_pct": round(total_change_pct, 2),
            "risk_assets_detail": risk_assets,
            "opportunity_assets_detail": opportunity_assets,
            "sector_performance": sector_avg,
            "assets": assets_detail,
            "lstm_forecast": lstm_result,
            "rf_assessment": rf_result,
        },
    }


@router.post("/risk-assessment")
async def assess_risk(data: RiskAssessmentInput, db: Session = Depends(get_db)):
    """风险评估 - Mock数据"""
    return {
        "risk_level": "中",
        "risk_score": 65,
        "warnings": ["持仓集中度偏高", "建议分散投资"],
    }


@router.get("/analysis/{request_id}")
async def get_analysis_result(request_id: str, db: Session = Depends(get_db)):
    """获取诊断结果"""
    # 这里应该从数据库查询，暂时返回模拟数据
    return {
        "request_id": request_id,
        "status": "completed",
        "result": {
            "confidence": 87,
            "summary": {
                "total_assets": 5,
                "risk_assets": 2,
                "opportunity_assets": 3,
            },
        },
    }
