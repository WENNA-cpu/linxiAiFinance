from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.rule_engine import check_question
from app.services.compliance_log_service import record_compliance_event
from app.services.deepseek_service import answer_diagnose_followup

router = APIRouter()


class DiagnosisContext(BaseModel):
    asset_name: Optional[str] = None
    interval: Optional[str] = None
    risk_level: Optional[str] = None
    change_pct: Optional[float] = None
    request_id: Optional[str] = None
    market_trend: Optional[str] = None
    sector_rotation: Optional[str] = None


class DiagnoseChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    diagnosis_context: DiagnosisContext = Field(default_factory=DiagnosisContext)


class DiagnoseChatResponse(BaseModel):
    answer: str
    model: str = "deepseek-chat"


@router.post("/chat", response_model=DiagnoseChatResponse)
async def diagnose_chat(body: DiagnoseChatRequest, db: Session = Depends(get_db)):
    """基于诊断结果的合规追问（服务端二次校验 + DeepSeek）"""
    question = body.question.strip()
    result = check_question(question)

    if result.is_blocked:
        record_compliance_event(
            db,
            question=question,
            action="blocked",
            blocked_reason=result.blocked_reason,
            matched_word=result.matched_word,
            request_id=body.diagnosis_context.request_id,
        )
        raise HTTPException(status_code=403, detail=result.blocked_reason)

    try:
        answer = await answer_diagnose_followup(question, body.diagnosis_context.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 问答服务异常: {str(e)[:100]}")

    return DiagnoseChatResponse(answer=answer)
