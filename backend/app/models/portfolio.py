from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, default="anonymous")
    total_value = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    total_return = Column(Float, default=0.0)
    total_return_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assets = relationship("Asset", back_populates="portfolio", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    code = Column(String, index=True)
    name = Column(String)
    type = Column(String)  # stock, fund, bond, other
    quantity = Column(Float, default=0.0)
    cost_price = Column(Float, default=0.0)
    current_price = Column(Float, default=0.0)
    market_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="assets")


class AIOutputLog(Base):
    __tablename__ = "ai_output_logs"

    id = Column(Integer, primary_key=True, index=True)
    output_id = Column(String, unique=True, index=True)
    request_id = Column(String, index=True)
    output_text = Column(Text)
    output_length = Column(Integer)
    model_used = Column(String, default="qwen3.6-plus")
    confidence = Column(Float, default=0.0)
    data_sources = Column(JSON, default=list)
    analysis_dimensions = Column(JSON, default=list)
    rule_checks = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    feedback_id = Column(String, unique=True, index=True)
    request_id = Column(String, index=True, nullable=True)  # 非唯一，同一诊断可有多条反馈
    output_id = Column(String, ForeignKey("ai_output_logs.output_id"), nullable=True)
    feedback_type = Column(String)  # positive, negative
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, index=True)
    step_name = Column(String)  # 步骤名称：数据获取、模型预测、规则校验等
    step_status = Column(String)  # 状态：成功/失败/进行中
    step_detail = Column(Text)  # 详细信息
    started_at = Column(DateTime, default=datetime.utcnow)  # 开始时间
    completed_at = Column(DateTime, nullable=True)  # 结束时间
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceLog(Base):
    __tablename__ = "compliance_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, index=True, nullable=True)
    question = Column(Text)
    action = Column(String, index=True)  # blocked / passed
    blocked_reason = Column(Text, nullable=True)
    matched_word = Column(String, nullable=True)
    source = Column(String, default="diagnose_followup")
    created_at = Column(DateTime, default=datetime.utcnow)
