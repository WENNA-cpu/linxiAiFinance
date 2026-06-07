from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.portfolio import ComplianceLog, AuditLog


def record_compliance_event(
    db: Session,
    *,
    question: str,
    action: str,
    blocked_reason: Optional[str] = None,
    matched_word: Optional[str] = None,
    request_id: Optional[str] = None,
    source: str = "diagnose_followup",
) -> ComplianceLog:
    """写入 compliance_logs，拦截时同步记审计日志供合规统计"""
    log = ComplianceLog(
        request_id=request_id,
        question=question[:500],
        action=action,
        blocked_reason=blocked_reason,
        matched_word=matched_word,
        source=source,
    )
    db.add(log)

    if action == "blocked":
        db.add(
            AuditLog(
                request_id=request_id or f"compliance_{int(datetime.utcnow().timestamp())}",
                step_name="合规问答拦截",
                step_status="失败",
                step_detail=(
                    f"来源={source}；命中词={matched_word or '-'}；"
                    f"问题={question[:120]}；原因={blocked_reason or '违规内容'}"
                ),
            )
        )

    db.commit()
    db.refresh(log)
    return log
