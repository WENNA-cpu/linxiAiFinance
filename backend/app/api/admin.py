from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.database import get_db
from app.models.portfolio import AIOutputLog, UserFeedback

router = APIRouter()


@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db)):
    """数据看板"""
    total_outputs = db.query(AIOutputLog).count()
    positive_feedback = db.query(UserFeedback).filter(UserFeedback.feedback_type == "positive").count()
    negative_feedback = db.query(UserFeedback).filter(UserFeedback.feedback_type == "negative").count()

    total_feedback = positive_feedback + negative_feedback
    usefulness_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0

    last_7_days = datetime.utcnow() - timedelta(days=7)
    recent_outputs = db.query(AIOutputLog).filter(AIOutputLog.created_at >= last_7_days).count()

    return {
        "overview": {
            "total_ai_outputs": total_outputs,
            "total_feedback": total_feedback,
            "usefulness_rate": round(usefulness_rate, 2),
            "recent_7d_outputs": recent_outputs,
        },
        "daily_stats": [
            {"date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"), "outputs": 10 + i * 2}
            for i in range(7)
        ],
        "feedback_distribution": {
            "positive": positive_feedback,
            "negative": negative_feedback,
        },
    }


@router.get("/feedback")
async def get_feedback(db: Session = Depends(get_db)):
    """用户反馈详情"""
    feedbacks = db.query(UserFeedback).order_by(UserFeedback.created_at.desc()).limit(50).all()

    return {
        "total": db.query(UserFeedback).count(),
        "feedbacks": [
            {
                "feedback_id": f.feedback_id,
                "output_id": f.output_id,
                "type": f.feedback_type,
                "reason": f.reason,
                "created_at": f.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for f in feedbacks
        ],
    }


@router.post("/feedback/export")
async def export_feedback(db: Session = Depends(get_db)):
    """导出反馈数据"""
    return {"message": "反馈数据导出功能", "format": "Excel"}
