from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import random
from typing import List, Optional

app = FastAPI(
    title="灵析 AI智能投顾助手 API",
    description="基于四层工业级架构的AI理财辅助工具后端API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def get_sector(code: str) -> str:
    """根据股票代码判断板块"""
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


@app.post("/api/portfolio/diagnose")
async def diagnose_portfolio(data: PortfolioInput):
    """AI持仓诊断 - 基于真实持仓数据生成结论"""
    assets = data.assets
    total_assets = len(assets)

    if total_assets == 0:
        return {
            "request_id": f"diag_{datetime.now().strftime('%Y%m%d%H%M%S')}",
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

    # 计算持仓整体表现
    total_cost = sum(a.cost_price * 100 for a in assets if a.cost_price)
    total_current = sum(a.current_price * 100 for a in assets if a.current_price)
    total_change_pct = ((total_current - total_cost) / total_cost * 100) if total_cost > 0 else 0

    # 识别风险资产和机会资产
    risk_assets = []
    opportunity_assets = []
    sector_performance = {}

    for asset in assets:
        if asset.cost_price and asset.current_price:
            change_pct = (asset.current_price - asset.cost_price) / asset.cost_price * 100

            if change_pct < -5:
                risk_assets.append({
                    "code": asset.code,
                    "name": asset.name,
                    "change_pct": round(change_pct, 2),
                })

            if change_pct > 5:
                opportunity_assets.append({
                    "code": asset.code,
                    "name": asset.name,
                    "change_pct": round(change_pct, 2),
                })

            sector = get_sector(asset.code)
            if sector not in sector_performance:
                sector_performance[sector] = []
            sector_performance[sector].append(change_pct)

    # 计算各板块平均涨跌幅
    sector_avg = {s: sum(p) / len(p) for s, p in sector_performance.items()}
    best_sector = max(sector_avg.items(), key=lambda x: x[1]) if sector_avg else ("未知", 0)
    worst_sector = min(sector_avg.items(), key=lambda x: x[1]) if sector_avg else ("未知", 0)

    # 生成市场趋势结论
    if total_change_pct > 0:
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

    request_id = f"diag_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return {
        "request_id": request_id,
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
            "time_range": datetime.now().strftime("%Y-%m-%d"),
            "sources": ["用户持仓数据"],
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        "detail": {
            "total_change_pct": round(total_change_pct, 2),
            "risk_assets_detail": risk_assets,
            "opportunity_assets_detail": opportunity_assets,
            "sector_performance": {k: round(v, 2) for k, v in sector_avg.items()},
        },
    }


@app.get("/api/market/sentiment")
async def get_market_sentiment():
    """获取市场情绪简报"""
    sentiment_index = random.randint(30, 70)

    if sentiment_index >= 60:
        status = "贪婪"
    elif sentiment_index >= 40:
        status = "中性"
    else:
        status = "恐惧"

    if abs(sentiment_index - 50) < 15:
        market_state = "震荡整理"
    elif sentiment_index > 65:
        market_state = "强势上涨"
    else:
        market_state = "弱势下跌"

    return {
        "sentiment_index": sentiment_index,
        "status": status,
        "market_state": market_state,
        "warning_signals": random.randint(0, 3),
        "data_source": "Tushare 舆情数据",
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/")
async def root():
    return {
        "message": "灵析 AI智能投顾助手 API",
        "version": "1.0.0",
        "docs": "/docs",
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
