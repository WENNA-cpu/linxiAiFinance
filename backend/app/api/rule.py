from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.rule_engine import check_question
from app.services.compliance_log_service import record_compliance_event

router = APIRouter()


class RuleCheckRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    request_id: Optional[str] = None


class RuleCheckResponse(BaseModel):
    is_blocked: bool
    blocked_reason: Optional[str] = None
    matched_word: Optional[str] = None


@router.post("/check", response_model=RuleCheckResponse)
async def check_rule(body: RuleCheckRequest, db: Session = Depends(get_db)):
    """合规问答前置检查：命中禁止词则拦截并记录 compliance_logs"""
    result = check_question(body.question)

    if result.is_blocked:
        record_compliance_event(
            db,
            question=body.question.strip(),
            action="blocked",
            blocked_reason=result.blocked_reason,
            matched_word=result.matched_word,
            request_id=body.request_id,
        )

    return RuleCheckResponse(
        is_blocked=result.is_blocked,
        blocked_reason=result.blocked_reason,
        matched_word=result.matched_word,
    )
