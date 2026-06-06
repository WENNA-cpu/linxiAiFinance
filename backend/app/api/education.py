from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.database import get_db
from app.services.education_service import list_courses, get_course
from app.services.deepseek_service import answer_education_question

router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(..., description="user 或 assistant")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="用户问题")
    history: Optional[List[ChatMessage]] = Field(default=None, description="对话历史")


class ChatResponse(BaseModel):
    answer: str
    model: str = "deepseek-chat"


@router.post("/chat", response_model=ChatResponse)
async def education_chat(body: ChatRequest):
    """投教 AI 问答助手"""
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    history = [{"role": m.role, "content": m.content} for m in (body.history or [])]

    try:
        answer = await answer_education_question(question, history)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 问答服务异常: {str(e)[:100]}")

    return ChatResponse(answer=answer)

@router.get("/courses")
async def get_courses(
    category: Optional[str] = Query("all", description="课程分类"),
    db: Session = Depends(get_db),
):
    """获取投教课程列表"""
    courses = list_courses(None if category in (None, "all") else category)
    return {
        "category": category or "all",
        "courses": courses,
        "total": len(courses),
        "data_source": "投教知识库",
    }


@router.get("/courses/{course_id}")
async def get_course_detail(course_id: int, db: Session = Depends(get_db)):
    """获取课程详情"""
    course = get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail=f"未找到课程 {course_id}")
    return course


@router.get("/{asset_type}")
async def get_education_content(
    asset_type: str,
    db: Session = Depends(get_db),
):
    """按资产类型获取投教内容（兼容旧接口）"""
    courses = list_courses(None if asset_type == "all" else asset_type)
    return {
        "asset_type": asset_type,
        "courses": courses,
        "total": len(courses),
    }
