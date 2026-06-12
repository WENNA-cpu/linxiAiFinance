import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.portfolio import UserFeedback

router = APIRouter()


class FeedbackCreate(BaseModel):
    request_id: str = Field(..., min_length=1)
    feedback_type: str = Field(..., min_length=1)
    reason: str = ""


def _normalize_feedback_type(feedback_type: str) -> str:
    normalized = feedback_type.strip().lower()
    if normalized in ("helpful", "positive", "有帮助"):
        return "positive"
    if normalized in ("unhelpful", "negative", "需改进"):
        return "negative"
    raise HTTPException(status_code=400, detail="feedback_type 无效，应为 helpful 或 unhelpful")


@router.post("/")
async def create_feedback(body: FeedbackCreate, db: Session = Depends(get_db)):
    """提交 AI 诊断反馈"""
    request_id = body.request_id.strip()
    if not request_id or request_id == "-":
        raise HTTPException(status_code=400, detail="无效的 request_id")

    feedback_type = _normalize_feedback_type(body.feedback_type)
    reason = body.reason.strip() or None

    feedback = UserFeedback(
        feedback_id=f"fb_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
        request_id=request_id,
        output_id=None,
        feedback_type=feedback_type,
        reason=reason,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return {
        "success": True,
        "message": "感谢您的反馈，这能帮助我们做得更好！",
        "feedback_id": feedback.feedback_id,
        "request_id": feedback.request_id,
        "feedback_type": feedback.feedback_type,
    }
