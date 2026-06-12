from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import get_db
from app.models.portfolio import AuditLog, ComplianceLog

router = APIRouter()


class RiskRatingInput(BaseModel):
    portfolio_id: int = 0


DEFAULT_RISK_RATING = {
    "rating": "中风险",
    "risk_level": "中风险",
    "risk_score": 65,
    "source": "暂无真实数据",
    "is_default": True,
}


@router.post("/rating")
async def get_risk_rating(data: RiskRatingInput, db: Session = Depends(get_db)):
    """风险评级：基于 compliance_logs 与 audit_logs 真实统计"""
    try:
        blocked = db.query(ComplianceLog).filter(ComplianceLog.action == "blocked").count()
        total_compliance = db.query(ComplianceLog).count()
        failed_audits = db.query(AuditLog).filter(
            AuditLog.step_status.in_(["失败", "警告"])
        ).count()
        total_audits = db.query(AuditLog).count()

        if total_compliance == 0 and total_audits == 0:
            return {
                "portfolio_id": data.portfolio_id,
                **DEFAULT_RISK_RATING,
                "risk_factors": [
                    {"name": "合规拦截", "level": "未知", "score": 0},
                    {"name": "审计异常", "level": "未知", "score": 0},
                ],
                "suggestions": ["导入持仓并完成诊断后，将基于真实审计数据更新风险评级"],
            }

        block_rate = (blocked / total_compliance) if total_compliance else 0
        fail_rate = (failed_audits / total_audits) if total_audits else 0
        risk_score = min(95, max(20, round(40 + block_rate * 30 + fail_rate * 40)))

        if risk_score >= 75:
            rating = "高风险"
        elif risk_score >= 50:
            rating = "中风险"
        else:
            rating = "低风险"

        return {
            "portfolio_id": data.portfolio_id,
            "rating": rating,
            "risk_level": rating,
            "risk_score": risk_score,
            "source": "compliance_logs + audit_logs",
            "is_default": False,
            "stats": {
                "compliance_blocked": blocked,
                "compliance_total": total_compliance,
                "audit_failed": failed_audits,
                "audit_total": total_audits,
            },
            "risk_factors": [
                {
                    "name": "合规拦截率",
                    "level": "高" if block_rate > 0.3 else "中" if block_rate > 0.1 else "低",
                    "score": round(block_rate * 100, 1),
                },
                {
                    "name": "审计异常率",
                    "level": "高" if fail_rate > 0.2 else "中" if fail_rate > 0.05 else "低",
                    "score": round(fail_rate * 100, 1),
                },
            ],
            "suggestions": [
                "建议分散投资，降低单只资产占比",
                "关注市场波动，适当控制仓位",
            ] if rating != "低风险" else ["当前系统审计风险指标处于较低水平"],
        }
    except Exception as e:
        print(f"[Risk Rating] 统计失败: {e}")
        return {
            "portfolio_id": data.portfolio_id,
            **DEFAULT_RISK_RATING,
            "risk_factors": [],
            "suggestions": ["风险数据暂不可用，请稍后重试"],
        }
