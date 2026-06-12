from app.core import env_loader  # noqa: F401 — 最先加载 .env

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import portfolio, market, cycle, risk, education, trace, admin, rule, diagnose_chat, feedback, value
from app.models.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="灵析 AI智能投顾助手 API",
    description="基于四层工业级架构的AI理财辅助工具后端API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router, prefix="/api/portfolio", tags=["持仓管理"])
app.include_router(market.router, prefix="/api/market", tags=["市场行情"])
app.include_router(cycle.router, prefix="/api/cycle", tags=["周期分析"])
app.include_router(risk.router, prefix="/api/risk", tags=["风险评估"])
app.include_router(education.router, prefix="/api/education", tags=["投教内容"])
app.include_router(trace.router, prefix="/api/trace", tags=["溯源查询"])
app.include_router(rule.router, prefix="/api/rule", tags=["合规规则"])
app.include_router(diagnose_chat.router, prefix="/api/diagnose", tags=["诊断追问"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["用户反馈"])
app.include_router(value.router, prefix="/api/value", tags=["商业价值"])


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
