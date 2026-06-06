from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.database import get_db

router = APIRouter()


@router.get("/{asset_type}")
async def get_education_content(
    asset_type: str = Path(..., description="资产类型: stock/fund/bond/portfolio/risk"),
    db: Session = Depends(get_db),
):
    """获取投教内容"""
    courses = [
        {
            "id": 1,
            "title": "股票估值基础：PE/PB指标详解",
            "category": "stock",
            "level": "入门",
            "duration": "15分钟",
            "completed": True,
            "recommended": True,
            "description": "学习市盈率(PE)和市净率(PB)的基本概念及应用场景",
        },
        {
            "id": 2,
            "title": "基金定投策略实战",
            "category": "fund",
            "level": "进阶",
            "duration": "25分钟",
            "completed": False,
            "recommended": True,
            "description": "掌握定投的核心逻辑，学会制定适合自己的定投计划",
        },
        {
            "id": 3,
            "title": "资产配置的四个维度",
            "category": "portfolio",
            "level": "进阶",
            "duration": "30分钟",
            "completed": False,
            "recommended": False,
            "description": "从风险、收益、流动性、时间四个维度构建投资组合",
        },
    ]

    if asset_type != "all":
        courses = [c for c in courses if c["category"] == asset_type]

    return {
        "asset_type": asset_type,
        "courses": courses,
        "total": len(courses),
    }
