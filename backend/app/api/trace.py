from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import traceback

from app.models.database import get_db
from app.models.portfolio import AuditLog
from app.services.trace_service import build_lineage_from_logs

router = APIRouter()


def _build_trace_response(request_id: str, logs: list) -> dict:
    log_list = []
    for index, log in enumerate(logs, start=1):
        log_list.append({
            "step_order": index,
            "step_name": log.step_name,
            "step_status": log.step_status,
            "step_detail": log.step_detail,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        })

    success_count = sum(1 for log in logs if log.step_status == "成功")
    failed_count = sum(1 for log in logs if log.step_status == "失败")
    warning_count = sum(1 for log in logs if log.step_status == "警告")
    data_sources = [log.step_detail for log in logs if log.step_name == "数据获取"]
    model_analysis = [log.step_detail for log in logs if "模型" in log.step_name]
    rule_checks = [log.step_detail for log in logs if "规则" in log.step_name]
    lineage = build_lineage_from_logs(logs)

    return {
        "request_id": request_id,
        "found": True,
        "generated_at": logs[0].created_at.isoformat() if logs else datetime.utcnow().isoformat(),
        "logs": log_list,
        "summary": {
            "total_steps": len(logs),
            "success_steps": success_count,
            "failed_steps": failed_count,
            "warning_steps": warning_count,
            "expected_steps": 7,
            "is_complete": len(logs) >= 7,
        },
        "data_sources": data_sources,
        "model_analysis": model_analysis,
        "rule_checks": rule_checks,
        "lineage": lineage,
    }


@router.get("/{request_id}/lineage")
async def get_trace_lineage(request_id: str, db: Session = Depends(get_db)):
    """获取数据处理血缘图"""
    logs = db.query(AuditLog).filter(AuditLog.request_id == request_id).order_by(AuditLog.id.asc()).all()
    if not logs:
        raise HTTPException(status_code=404, detail=f"未找到 {request_id} 的溯源记录")
    return build_lineage_from_logs(logs)


@router.get("/{request_id}")
async def get_trace(request_id: str, db: Session = Depends(get_db)):
    """获取诊断溯源信息"""
    try:
        logs = db.query(AuditLog).filter(AuditLog.request_id == request_id).order_by(AuditLog.created_at.asc()).all()
        if not logs:
            raise HTTPException(
                status_code=404,
                detail=f"未找到 {request_id} 的溯源信息，请先完成一次持仓诊断",
            )
        return _build_trace_response(request_id, logs)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Trace API Error] request_id={request_id}, error={str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"溯源查询失败: {str(e)[:100]}")
