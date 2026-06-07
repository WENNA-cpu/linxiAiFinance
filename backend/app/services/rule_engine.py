"""合规规则引擎 — 禁止词汇拦截（与前端合规页、风控模块保持一致）"""

from dataclasses import dataclass
from typing import Optional, List

FORBIDDEN_WORDS: List[str] = [
    "荐股",
    "推荐股票",
    "涨停",
    "抄底",
    "内幕消息",
    "保证收益",
    "稳赚",
    "能买吗",
    "能卖吗",
    "什么时候卖",
]


@dataclass
class RuleCheckResult:
    is_blocked: bool
    blocked_reason: Optional[str] = None
    matched_word: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "is_blocked": self.is_blocked,
            "blocked_reason": self.blocked_reason,
            "matched_word": self.matched_word,
        }


def check_question(question: str) -> RuleCheckResult:
    """检测用户问题是否命中禁止词库"""
    text = (question or "").strip()
    if not text:
        return RuleCheckResult(
            is_blocked=True,
            blocked_reason="问题不能为空",
            matched_word=None,
        )

    lowered = text.lower()
    for word in FORBIDDEN_WORDS:
        if word in text or word.lower() in lowered:
            return RuleCheckResult(
                is_blocked=True,
                blocked_reason=f"问题包含禁止词汇「{word}」，该问题已被合规规则拦截",
                matched_word=word,
            )

    return RuleCheckResult(is_blocked=False)
