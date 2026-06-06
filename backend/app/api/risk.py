from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import get_db

router = APIRouter()


class RiskRatingInput(BaseModel):
    portfolio_id: int


@router.post("/rating")
async def get_risk_rating(data: RiskRatingInput, db: Session = Depends(get_db)):
    """风险评级（随机森林模型）"""
    return {
        "portfolio_id": data.portfolio_id,
        "risk_level": "中等",
        "risk_score": 65,
        "risk_factors": [
            {"name": "集中度风险", "level": "高", "score": 75},
            {"name": "波动性风险", "level": "中", "score": 60},
            {"name": "流动性风险", "level": "低", "score": 40},
        ],
        "suggestions": [
            "建议分散投资，降低单只资产占比",
            "关注市场波动，适当控制仓位",
        ],
    }
