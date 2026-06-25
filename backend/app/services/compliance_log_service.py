from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.portfolio import ComplianceLog

_DEDUP_WINDOW_SECONDS = 30


def _find_recent_duplicate(
    db: Session,
    *,
    question: str,
    action: str,
    request_id: Optional[str],
) -> Optional[ComplianceLog]:
    """短时间内的相同拦截视为重复提交，避免双写日志"""
    since = datetime.utcnow() - timedelta(seconds=_DEDUP_WINDOW_SECONDS)
    query = db.query(ComplianceLog).filter(
        ComplianceLog.question == question[:500],
        ComplianceLog.action == action,
        ComplianceLog.created_at >= since,
    )
    if request_id:
        query = query.filter(ComplianceLog.request_id == request_id)
    return query.order_by(ComplianceLog.created_at.desc()).first()


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
    """写入 compliance_logs（问答拦截的唯一计数来源，避免与 audit_logs 重复统计）"""
    normalized = question.strip()
    existing = _find_recent_duplicate(
        db,
        question=normalized,
        action=action,
        request_id=request_id,
    )
    if existing:
        return existing

    log = ComplianceLog(
        request_id=request_id,
        question=normalized[:500],
        action=action,
        blocked_reason=blocked_reason,
        matched_word=matched_word,
        source=source,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
