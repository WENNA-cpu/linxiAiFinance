from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import traceback

from app.models.database import get_db
from app.models.portfolio import AuditLog

router = APIRouter()


def generate_mock_trace_data(request_id: str):
    """生成 Mock 溯源数据"""
    now = datetime.utcnow()
    logs = [
        {
            "step_name": "请求接收",
            "step_status": "成功",
            "step_detail": "用户发起持仓诊断请求",
            "started_at": now.isoformat(),
            "completed_at": (now.replace(microsecond=now.microsecond + 100000)).isoformat(),
        },
        {
            "step_name": "数据获取",
            "step_status": "成功",
            "step_detail": "从Tushare行情数据、用户持仓数据获取行情数据，共3只资产",
            "started_at": (now.replace(microsecond=now.microsecond + 100000)).isoformat(),
            "completed_at": (now.replace(microsecond=now.microsecond + 500000)).isoformat(),
        },
        {
            "step_name": "数据清洗",
            "step_status": "成功",
            "step_detail": "完成缺失值处理和格式转换",
            "started_at": (now.replace(microsecond=now.microsecond + 500000)).isoformat(),
            "completed_at": (now.replace(microsecond=now.microsecond + 800000)).isoformat(),
        },
        {
            "step_name": "LSTM模型预测",
            "step_status": "成功",
            "step_detail": "完成时序分析和趋势预测",
            "started_at": (now.replace(microsecond=now.microsecond + 800000)).isoformat(),
            "completed_at": (now.replace(microsecond=now.microsecond + 1200000)).isoformat(),
        },
        {
            "step_name": "随机森林风险评估",
            "step_status": "成功",
            "step_detail": "识别出3个风险资产",
            "started_at": (now.replace(microsecond=now.microsecond + 1200000)).isoformat(),
            "completed_at": (now.replace(microsecond=now.microsecond + 1500000)).isoformat(),
        },
        {
            "step_name": "规则引擎校验",
            "step_status": "成功",
            "step_detail": "通过所有风控规则校验",
            "started_at": (now.replace(microsecond=now.microsecond + 1500000)).isoformat(),
            "completed_at": (now.replace(microsecond=now.microsecond + 1800000)).isoformat(),
        },
        {
            "step_name": "结果生成",
            "step_status": "成功",
            "step_detail": "诊断报告生成完毕",
            "started_at": (now.replace(microsecond=now.microsecond + 1800000)).isoformat(),
            "completed_at": (now.replace(microsecond=now.microsecond + 2000000)).isoformat(),
        },
    ]

    return {
        "request_id": request_id,
        "found": True,
        "generated_at": now.isoformat(),
        "logs": logs,
        "summary": {
            "total_steps": len(logs),
            "success_steps": len(logs),
            "failed_steps": 0,
        },
        "data_sources": [
            "从Tushare行情数据、用户持仓数据获取行情数据，共3只资产"
        ],
        "model_analysis": [
            "完成时序分析和趋势预测",
            "识别出3个风险资产"
        ],
        "rule_checks": [
            "通过所有风控规则校验"
        ],
        "is_mock": True,
    }


@router.get("/{request_id}")
async def get_trace(request_id: str, db: Session = Depends(get_db)):
    """获取诊断溯源信息"""
    try:
        # 查询审计日志
        logs = db.query(AuditLog).filter(AuditLog.request_id == request_id).order_by(AuditLog.created_at.asc()).all()

        if not logs:
            # 未找到数据，返回 Mock 数据
            mock_data = generate_mock_trace_data(request_id)
            mock_data["message"] = "未找到该次诊断的溯源信息，返回演示数据"
            return mock_data

        # 构建日志列表
        log_list = []
        for log in logs:
            log_list.append({
                "step_name": log.step_name,
                "step_status": log.step_status,
                "step_detail": log.step_detail,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            })

        # 计算统计
        success_count = sum(1 for log in logs if log.step_status == "成功")
        failed_count = sum(1 for log in logs if log.step_status == "失败")

        # 提取数据源信息
        data_sources = [log.step_detail for log in logs if "数据获取" in log.step_name or "Tushare" in log.step_detail]

        # 提取模型分析信息
        model_analysis = [log.step_detail for log in logs if "模型" in log.step_name or "预测" in log.step_name]

        # 提取规则校验信息
        rule_checks = [log.step_detail for log in logs if "规则" in log.step_name or "校验" in log.step_name]

        return {
            "request_id": request_id,
            "found": True,
            "generated_at": logs[0].created_at.isoformat() if logs else datetime.utcnow().isoformat(),
            "logs": log_list,
            "summary": {
                "total_steps": len(logs),
                "success_steps": success_count,
                "failed_steps": failed_count,
            },
            "data_sources": data_sources,
            "model_analysis": model_analysis,
            "rule_checks": rule_checks,
        }
    except Exception as e:
        # 捕获所有异常，打印日志并返回 Mock 数据
        print(f"[Trace API Error] request_id={request_id}, error={str(e)}")
        print(f"[Trace API Error] traceback={traceback.format_exc()}")

        # 返回 Mock 数据，确保前端正常展示
        mock_data = generate_mock_trace_data(request_id)
        mock_data["message"] = f"数据库查询异常，返回演示数据。错误：{str(e)[:100]}"
        mock_data["error_detail"] = str(e)
        return mock_data
