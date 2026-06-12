from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.portfolio import AuditLog, ComplianceLog, UserFeedback

router = APIRouter()

DEFAULT_VALUE_STATS = {
    "time_saved_hours": 156,
    "holding_days": 23,
    "loss_avoided": 8500,
    "source": "演示估算模型（暂无用户使用数据）",
    "is_estimated": True,
}


@router.get("/stats")
async def get_value_stats(db: Session = Depends(get_db)):
    """
    商业价值估算：基于诊断次数、合规拦截与用户反馈动态计算。
    无数据时返回带说明的默认估算值。
    """
    try:
        total_diagnoses = db.query(AuditLog).filter(
            AuditLog.step_name == "请求接收"
        ).count()
        blocked_count = db.query(ComplianceLog).filter(
            ComplianceLog.action == "blocked"
        ).count()
        feedback_count = db.query(UserFeedback).count()

        if total_diagnoses == 0 and blocked_count == 0 and feedback_count == 0:
            return {
                **DEFAULT_VALUE_STATS,
                "diagnosis_count": 0,
                "blocked_count": 0,
                "feedback_count": 0,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        # 每次诊断约节省 25 分钟；年化按诊断次数 × 12 估算
        minutes_saved = total_diagnoses * 25
        time_saved_hours = max(24, round(minutes_saved * 12 / 60))

        # 合规拦截越多，估算减少冲动交易带来的持有期延长
        holding_days = min(60, max(7, 10 + blocked_count * 2 + total_diagnoses // 5))

        # 情绪/合规价值：基础 + 诊断与拦截加权
        loss_avoided = min(50000, max(3000, 2000 + total_diagnoses * 800 + blocked_count * 500))

        return {
            "time_saved_hours": time_saved_hours,
            "holding_days": holding_days,
            "loss_avoided": loss_avoided,
            "source": "基于系统审计与合规日志估算",
            "is_estimated": True,
            "diagnosis_count": total_diagnoses,
            "blocked_count": blocked_count,
            "feedback_count": feedback_count,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        print(f"[Value Stats] 计算失败，返回默认值: {e}")
        return {
            **DEFAULT_VALUE_STATS,
            "diagnosis_count": 0,
            "blocked_count": 0,
            "feedback_count": 0,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
