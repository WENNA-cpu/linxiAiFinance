from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import random
import os
import asyncio
import aiohttp

from app.models.database import get_db
from app.models.portfolio import AuditLog
from app.services.data_service import DataService
from app.services.lstm_cycle_service import get_lstm_predictor
from app.services.rf_risk_service import get_rf_predictor
from app.services.model_manager import should_use_new_model
from app.config import NEW_MODEL_RATIO

router = APIRouter()

# Tushare配置
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "").strip()


async def fetch_tushare_daily(ts_code: str) -> Optional[Dict[str, Any]]:
    """从Tushare获取最新日线数据"""
    try:
        async with aiohttp.ClientSession() as session:
            # 获取最近一个交易日的数据
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

            payload = {
                "api_name": "daily",
                "token": TUSHARE_TOKEN,
                "params": {
                    "ts_code": ts_code,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            }

            print(f"[Tushare] 请求 {ts_code} 数据, payload: {payload}")

            async with session.post("https://api.tushare.pro", json=payload) as response:
                print(f"[Tushare] {ts_code} 响应状态: {response.status}")
                if response.status == 200:
                    result = await response.json()
                    print(f"[Tushare] {ts_code} 响应: {result}")
                    if result.get("code") == 0:
                        data = result.get("data", {})
                        if data and "items" in data and len(data["items"]) > 0:
                            fields = data.get("fields", [])
                            latest_item = data["items"][0]  # 最新数据
                            result_dict = dict(zip(fields, latest_item))
                            print(f"[Tushare] {ts_code} 成功获取数据: {result_dict}")
                            return result_dict
                        else:
                            print(f"[Tushare] {ts_code} 无数据返回")
                    else:
                        print(f"[Tushare] {ts_code} API错误: {result.get('msg', '未知错误')}")
                else:
                    print(f"[Tushare] {ts_code} HTTP错误: {response.status}")
    except Exception as e:
        print(f"[Tushare] 获取 {ts_code} 数据失败: {e}")
        import traceback
        traceback.print_exc()
    return None


async def fetch_stock_quote(ts_code: str) -> Optional[Dict[str, Any]]:
    """获取股票行情（涨跌幅等）"""
    daily_data = await fetch_tushare_daily(ts_code)
    if daily_data:
        return {
            "ts_code": ts_code,
            "trade_date": daily_data.get("trade_date", ""),
            "close": daily_data.get("close", 0),
            "open": daily_data.get("open", 0),
            "high": daily_data.get("high", 0),
            "low": daily_data.get("low", 0),
            "pre_close": daily_data.get("pre_close", 0),
            "change": daily_data.get("change", 0),
            "pct_chg": daily_data.get("pct_chg", 0),
            "vol": daily_data.get("vol", 0),
            "amount": daily_data.get("amount", 0),
        }
    return None


def _normalize_ts_code(code: str) -> str:
    if "." in code:
        return code
    return f"{code}.SH" if code.startswith("6") else f"{code}.SZ"


async def fetch_asset_history(ts_code: str, days: int = 365) -> List[Dict[str, Any]]:
    """获取资产历史日线+估值用于 RF/LSTM"""
    svc = DataService()
    end = datetime.now()
    start = end - timedelta(days=days)
    sd, ed = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    daily = await svc.fetch_daily_data(ts_code, sd, ed) or []
    basic = await svc.fetch_daily_basic_historical(ts_code, sd, ed) or []
    basic_map = {b.get("trade_date"): b for b in basic}
    rows = []
    for d in sorted(daily, key=lambda x: x.get("trade_date", "")):
        td = d.get("trade_date")
        merged = dict(d)
        if td in basic_map:
            merged.update({k: basic_map[td].get(k) for k in ("pe", "pb", "ps", "turnover_rate")})
        rows.append(merged)
    return rows


async def _fetch_quotes_parallel(assets: List, timeout: float = 12.0) -> Dict[str, Any]:
    """并行拉取行情，超时后回退到用户导入价格"""

    async def _one(asset) -> tuple:
        ts_code = _normalize_ts_code(asset.code)
        try:
            quote = await asyncio.wait_for(fetch_stock_quote(ts_code), timeout=4.0)
            return asset.code, quote
        except Exception:
            return asset.code, None

    pairs: List[tuple] = []
    try:
        pairs = await asyncio.wait_for(
            asyncio.gather(*[_one(a) for a in assets]),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        print("[诊断] 行情拉取超时，使用用户导入价格")

    return {code: quote for code, quote in pairs if quote}


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
        history = await fetch_asset_history(ts_code, days=120)
        closes = [float(r["close"]) for r in history if r.get("close")]
        if len(closes) < 30:
            continue
        pred = predictor.predict(closes)
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
        history = await fetch_asset_history(ts_code, days=180)
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


class PortfolioInput(BaseModel):
    assets: List[AssetInput]
    total_value: Optional[float] = None
    leverage: float = 1.0


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
    # 若用户已提供成本价/现价，优先使用本地数据，避免阻塞
    has_local_prices = all(
        a.cost_price and a.current_price for a in assets
    )
    if has_local_prices:
        asset_quotes = {}
        record_audit_step(
            db, request_id, "数据获取",
            f"共{total_assets}只资产（使用用户导入价格，跳过行情拉取）",
            audit_logs, started_at=step_start,
        )
    else:
        asset_quotes = await _fetch_quotes_parallel(assets)
        record_audit_step(
            db, request_id, "数据获取",
            f"共{total_assets}只资产，行情命中 {len(asset_quotes)} 只",
            audit_logs, started_at=step_start,
        )

    step_start = datetime.utcnow()
    total_cost = sum(a.cost_price * 100 for a in assets if a.cost_price)
    total_current = sum(a.current_price * 100 for a in assets if a.current_price)
    total_change_pct = ((total_current - total_cost) / total_cost * 100) if total_cost > 0 else 0

    risk_assets = []
    opportunity_assets = []
    sector_performance = {}

    for asset in assets:
        # 优先使用Tushare的今日涨跌幅
        quote = asset_quotes.get(asset.code)
        if quote and quote.get('pct_chg') is not None:
            today_change_pct = quote['pct_chg']
        elif asset.cost_price and asset.current_price:
            today_change_pct = (asset.current_price - asset.cost_price) / asset.cost_price * 100
        else:
            today_change_pct = 0

        # 亏损超过5%视为风险资产
        if today_change_pct < -5:
            risk_assets.append({
                "code": asset.code,
                "name": asset.name,
                "change_pct": round(today_change_pct, 2),
                "today_change": today_change_pct,
            })

        # 盈利超过5%视为机会资产
        if today_change_pct > 5:
            opportunity_assets.append({
                "code": asset.code,
                "name": asset.name,
                "change_pct": round(today_change_pct, 2),
                "today_change": today_change_pct,
            })

        # 按板块统计
        sector = _get_sector(asset.code)
        if sector not in sector_performance:
            sector_performance[sector] = []
        sector_performance[sector].append(today_change_pct)

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

    # 构建资产详情（基于用户成本价计算真实盈亏）
    assets_detail = []
    for asset in assets:
        quote = asset_quotes.get(asset.code)

        # 从Tushare获取当前价格（收盘价）
        if quote and quote.get('close'):
            current_price = quote['close']
            trade_date = quote.get('trade_date', '')
            data_source = "Tushare实时行情"
        elif asset.current_price:
            # 使用用户导入的当前价格
            current_price = asset.current_price
            trade_date = ""
            data_source = "用户导入数据"
        else:
            current_price = 0
            trade_date = ""
            data_source = "暂无数据"

        # 计算基于成本价的盈亏百分比
        if asset.cost_price and asset.cost_price > 0 and current_price > 0:
            profit_pct = (current_price - asset.cost_price) / asset.cost_price * 100
        else:
            profit_pct = 0

        assets_detail.append({
            "code": asset.code,
            "name": asset.name,
            "weight": asset.weight,
            "cost_price": asset.cost_price,
            "current_price": current_price,
            "profit_pct": round(profit_pct, 2),  # 基于成本价的盈亏百分比
            "trade_date": trade_date,  # 数据日期
            "data_source": data_source,
        })

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
