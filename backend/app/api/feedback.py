import uuid

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


@router.post("", include_in_schema=True)
@router.post("/", include_in_schema=True)
async def create_feedback(body: FeedbackCreate, db: Session = Depends(get_db)):
    """提交 AI 诊断反馈（每次提交 INSERT 新记录，同一 request_id 可并存多条）"""
    request_id = body.request_id.strip()
    if not request_id or request_id == "-":
        raise HTTPException(status_code=400, detail="无效的 request_id")

    feedback_type = _normalize_feedback_type(body.feedback_type)
    if feedback_type == "positive":
        reason = None
    else:
        reason = body.reason.strip() or None

    feedback = UserFeedback(
        feedback_id=f"fb_{uuid.uuid4().hex}",
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
        "id": feedback.id,
        "feedback_id": feedback.feedback_id,
        "request_id": feedback.request_id,
        "feedback_type": _to_public_feedback_type(feedback.feedback_type),
    }


def _to_public_feedback_type(feedback_type: str) -> str:
    if feedback_type == "positive":
        return "helpful"
    if feedback_type == "negative":
        return "unhelpful"
    return feedback_type


@router.get("/by-request/{request_id}")
async def get_feedback_by_request(request_id: str, db: Session = Depends(get_db)):
    """查询指定诊断 request_id 的用户反馈"""
    rid = request_id.strip()
    if not rid or rid == "-":
        raise HTTPException(status_code=400, detail="无效的 request_id")

    rows = (
        db.query(UserFeedback)
        .filter(UserFeedback.request_id == rid)
        .order_by(UserFeedback.created_at.desc())
        .all()
    )

    return {
        "feedbacks": [
            {
                "id": row.id,
                "feedback_type": _to_public_feedback_type(row.feedback_type),
                "reason": row.reason,
                "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else None,
            }
            for row in rows
        ]
    }
