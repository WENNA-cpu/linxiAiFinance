import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_COURSES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "courses_full.json"


def _load_courses_raw() -> List[Dict[str, Any]]:
    """每次从 JSON 文件读取，方便后台直接更新文件后即时生效"""
    if not _COURSES_PATH.exists():
        print(f"[Education] 课程文件不存在: {_COURSES_PATH}")
        return []

    try:
        with open(_COURSES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[Education] 读取课程文件失败: {e}")
        return []


def get_courses_updated_at() -> Optional[str]:
    if not _COURSES_PATH.exists():
        return None
    mtime = _COURSES_PATH.stat().st_mtime
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")


def _load_courses() -> List[Dict[str, Any]]:
    return _load_courses_raw()


def list_courses(category: Optional[str] = None) -> List[Dict[str, Any]]:
    courses = _load_courses()
    result = []
    for course in courses:
        item = {
            "id": course["id"],
            "title": course["title"],
            "category": course["category"],
            "categoryName": course.get("categoryName", course["category"]),
            "level": course["level"],
            "duration": course["duration"],
            "completed": course.get("completed", False),
            "recommended": course.get("recommended", False),
            "description": course.get("description", ""),
            "section_count": len(course.get("sections", [])),
        }
        result.append(item)

    if category and category != "all":
        result = [c for c in result if c["category"] == category]
    return result


def get_course(course_id: int) -> Optional[Dict[str, Any]]:
    for course in _load_courses():
        if course["id"] == course_id:
            return course
    return None
