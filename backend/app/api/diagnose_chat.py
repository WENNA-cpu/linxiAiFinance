import re
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.compliance_log_service import record_compliance_event
from app.services.data_service import DataService
from app.services.deepseek_service import _format_diagnosis_context, chat_completion
from app.services.rule_engine import check_question

router = APIRouter()

_CODE_RE = re.compile(r"\b(\d{6})\b")
_STOCK_NAME_RE = re.compile(
    r"([^\s，,。.?？!！、；;]{2,10})(?:怎么样|咋样|如何|怎样|好不好|什么水平|近期表现|值得关注吗|介绍一下|是啥|是什么|咋样啊|如何啊)"
)
_STOCK_NAME_LOOSE_RE = re.compile(r"([^\s，,。.?？!！、；;]{2,8})(?:股|矿业|银行|科技|医药|能源|证券|基金|ETF)?")
_SKIP_NAMES = frozenset(
    {"我的", "这个", "那个", "这只", "那只", "整体", "持仓", "组合", "市场", "大盘", "风险", "诊断"}
)

_stock_basic_cache: list[dict[str, Any]] | None = None
_stock_basic_cache_at: float = 0.0
_STOCK_BASIC_TTL = 86400


class AssetContextItem(BaseModel):
    name: str
    ts_code: Optional[str] = None
    code: Optional[str] = None
    change_pct: Optional[float] = None
    today_change_pct: Optional[float] = None
    risk_level: Optional[str] = None
    cost_price: Optional[float] = None
    current_price: Optional[float] = None
    quantity: Optional[float] = None


class DiagnosisSummary(BaseModel):
    total_change: Optional[float] = None
    total_assets: Optional[int] = None
    market_trend: Optional[str] = None
    sector_rotation: Optional[str] = None


class DiagnosisContext(BaseModel):
    assets: Optional[list[AssetContextItem]] = None
    summary: Optional[DiagnosisSummary] = None
    # 兼容旧版单资产字段
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
    blocked: bool = False
    message: Optional[str] = None
    answer: Optional[str] = None
    model: Optional[str] = None


def _bare_code(code: str) -> str:
    return code.strip().upper().replace(".SH", "").replace(".SZ", "")


def _asset_codes(asset: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    for key in ("code", "ts_code"):
        raw = asset.get(key)
        if raw:
            codes.add(_bare_code(str(raw)))
    return codes


def _portfolio_names_and_codes(assets: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    held_codes: set[str] = set()
    held_names: set[str] = set()
    for asset in assets:
        held_codes.update(_asset_codes(asset))
        name = (asset.get("name") or "").strip()
        if name:
            held_names.add(name)
    return held_names, held_codes


def _name_in_portfolio(name: str, held_names: set[str]) -> bool:
    if not name:
        return False
    if name in held_names:
        return True
    for held in held_names:
        if name in held or held in name:
            return True
    return False


def _find_portfolio_match(question: str, assets: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not assets:
        return None

    held_names, _ = _portfolio_names_and_codes(assets)

    for match in _CODE_RE.finditer(question):
        bare = match.group(1)
        for asset in assets:
            if bare in _asset_codes(asset):
                return asset

    for asset in sorted(assets, key=lambda item: len(item.get("name") or ""), reverse=True):
        name = (asset.get("name") or "").strip()
        if name and name in question:
            return asset

    for asset in assets:
        name = (asset.get("name") or "").strip()
        if not name or len(name) < 2:
            continue
        for alias in (name[-2:], name[:2], name.replace("贵州", "").strip()):
            if alias and len(alias) >= 2 and alias in question and _name_in_portfolio(name, held_names):
                return asset

    return None


def _extract_external_stock_hint(question: str, assets: list[dict[str, Any]]) -> Optional[dict[str, str]]:
    held_names, held_codes = _portfolio_names_and_codes(assets)

    for match in _CODE_RE.finditer(question):
        bare = match.group(1)
        if bare not in held_codes:
            return {"code": bare}

    name_match = _STOCK_NAME_RE.search(question)
    if name_match:
        name = name_match.group(1).strip()
        if name not in _SKIP_NAMES and not _name_in_portfolio(name, held_names):
            return {"name": name}

    loose_match = _STOCK_NAME_LOOSE_RE.search(question)
    if loose_match:
        name = loose_match.group(1).strip()
        if name not in _SKIP_NAMES and not _name_in_portfolio(name, held_names):
            return {"name": name}

    return None


async def _find_external_stock_in_question(
    question: str,
    assets: list[dict[str, Any]],
) -> Optional[tuple[str, str]]:
    """从 stock_basic 中扫描问题里提到的、且不在持仓中的标的"""
    held_names, held_codes = _portfolio_names_and_codes(assets)
    stock_basic = await _get_stock_basic()
    if not stock_basic:
        return None

    hits: list[tuple[str, str, int]] = []
    for row in stock_basic:
        name = str(row.get("name") or "").strip()
        ts_code = str(row.get("ts_code") or "")
        bare = _bare_code(ts_code)
        if not name or not bare:
            continue
        if name in question and not _name_in_portfolio(name, held_names):
            hits.append((name, bare, len(name)))

    if hits:
        hits.sort(key=lambda item: item[2], reverse=True)
        best_name, best_code, _ = hits[0]
        return best_name, best_code

    for match in _CODE_RE.finditer(question):
        bare = match.group(1)
        if bare in held_codes:
            continue
        ts_code = DataService._normalize_ts_code(bare)
        for row in stock_basic:
            if row.get("ts_code") == ts_code:
                return str(row.get("name") or bare), bare
        return bare, bare

    return None


async def _get_stock_basic() -> list[dict[str, Any]]:
    global _stock_basic_cache, _stock_basic_cache_at

    now = time.time()
    if _stock_basic_cache is not None and now - _stock_basic_cache_at < _STOCK_BASIC_TTL:
        return _stock_basic_cache

    svc = DataService()
    data = await svc.fetch_stock_basic()
    _stock_basic_cache = data or []
    _stock_basic_cache_at = now
    return _stock_basic_cache


async def _resolve_external_stock(hint: dict[str, str]) -> tuple[str, str]:
    stock_name = hint.get("name", "").strip()
    stock_code = _bare_code(hint.get("code", ""))

    stock_basic = await _get_stock_basic()
    if stock_basic:
        if stock_code:
            ts_code = DataService._normalize_ts_code(stock_code)
            for row in stock_basic:
                if row.get("ts_code") == ts_code:
                    return str(row.get("name") or stock_name or stock_code), stock_code
        if stock_name:
            for row in stock_basic:
                if row.get("name") == stock_name:
                    bare = _bare_code(str(row.get("ts_code") or ""))
                    return stock_name, bare

    if stock_name and not stock_code:
        return stock_name, ""
    if stock_code and not stock_name:
        return stock_code, stock_code
    return stock_name or stock_code, stock_code


def _format_ts_code(stock_code: str) -> str:
    code = (stock_code or "").strip().upper()
    if not code:
        return ""
    if "." in code:
        return code
    return DataService._normalize_ts_code(code)


def _format_price(value: Any) -> str:
    if value is None:
        return "暂无"
    return f"{float(value):.2f}"


def _format_pct(value: Any) -> str:
    if value is None:
        return "暂无"
    return f"{float(value):.2f}%"


def build_prompt(
    mode: str,
    question: str,
    *,
    stock_name: str = "",
    stock_code: str = "",
    focus_asset: Optional[dict[str, Any]] = None,
    diagnosis_context: Optional[dict[str, Any]] = None,
) -> tuple[str, str]:
    """构建 DeepSeek 的 system / user Prompt"""
    q = question.strip()

    if mode == "external":
        display_code = _format_ts_code(stock_code) or stock_code or "未知"
        system_prompt = (
            "你是「灵析 AI 智能投顾助手」的投教解读助手。"
            "请基于公开信息，为用户提供有参考价值的客观分析。"
            "回答须充实、结构清晰，篇幅 150-300 字。"
            "严禁给出买入、卖出、持有等具体操作建议，不得承诺收益或预测涨跌。"
        )
        user_prompt = (
            f"请介绍一下【{stock_name}】（{display_code}）这家公司，包含以下维度：\n\n"
            "主营业务：公司主要做什么？\n"
            "近期表现：近半年股价走势、成交量变化\n"
            "估值水平：当前 PE/PB 处于历史什么位置\n"
            "行业前景：所属行业近期有什么变化？\n"
            "机构观点：主流券商最近怎么看？（中性/谨慎/看好）\n\n"
            "要求：\n"
            "- 信息要有参考价值，不少于 150 字\n"
            "- 不要给出「买入」「卖出」「持有」等具体操作建议\n"
            "- 结尾加上提示：「以上信息仅供参考，不构成投资建议」\n\n"
            f"股票：【{stock_name}】（{display_code}）\n\n"
            f"用户原始问题：{q}"
        )
        return system_prompt, user_prompt

    if mode == "portfolio" and focus_asset:
        name = focus_asset.get("name") or "该资产"
        cost = _format_price(focus_asset.get("cost_price"))
        current = _format_price(focus_asset.get("current_price"))
        pnl = _format_pct(focus_asset.get("change_pct"))
        ts_code = focus_asset.get("ts_code") or focus_asset.get("code") or ""
        code_part = f"（{ts_code}）" if ts_code else ""

        system_prompt = (
            "你是「灵析 AI 智能投顾助手」的持仓诊断解读助手。"
            "仅基于提供的真实持仓数据客观解读，回答 150-300 字，条理清晰。"
            "严禁给出买入、卖出、持有等具体操作建议，不得承诺收益或预测涨跌。"
        )
        user_prompt = (
            f"您的持仓：【{name}】{code_part}，成本价【{cost}】，当前价【{current}】，盈亏【{pnl}】。\n\n"
            "请结合以上持仓信息，回答用户问题。开头可以说「您持有的...」，但不要给出买卖建议。\n\n"
            f"用户问题：{q}"
        )
        return system_prompt, user_prompt

    # 组合整体问题（未指向具体持仓外标的）
    context_block = _format_diagnosis_context(diagnosis_context or {})
    system_prompt = (
        "你是「灵析 AI 智能投顾助手」的持仓诊断解读助手。"
        "仅基于提供的完整持仓诊断结果客观解读，回答 150-300 字。"
        "严禁给出具体买卖建议，不得承诺收益或预测涨跌。"
    )
    user_prompt = (
        f"用户持仓诊断结果：\n{context_block}\n\n"
        f"用户问题：{q}\n\n"
        "请基于以上诊断结果回答，不要给出具体的买卖建议。"
    )
    return system_prompt, user_prompt


async def _call_deepseek(system_prompt: str, user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = await chat_completion(messages)
    if "error" in response:
        raise RuntimeError(response["error"])

    choices = response.get("choices", [])
    if not choices:
        raise RuntimeError("DeepSeek 未返回有效回答")

    content = choices[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("DeepSeek 返回内容为空")
    return content


async def chat_with_diagnose(body: DiagnoseChatRequest, db: Session) -> DiagnoseChatResponse:
    """基于诊断结果的合规追问（规则引擎 + DeepSeek）"""
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
        return DiagnoseChatResponse(
            blocked=True,
            message=result.blocked_reason or "该问题已被合规规则拦截",
        )

    context = body.diagnosis_context.model_dump()
    assets = context.get("assets") or []
    matched_asset = _find_portfolio_match(question, assets)

    try:
        if matched_asset:
            system_prompt, user_prompt = build_prompt(
                "portfolio",
                question,
                focus_asset=matched_asset,
            )
        else:
            external = await _find_external_stock_in_question(question, assets)
            if not external:
                hint = _extract_external_stock_hint(question, assets)
                if hint:
                    external = await _resolve_external_stock(hint)

            if external:
                stock_name, stock_code = external
                system_prompt, user_prompt = build_prompt(
                    "external",
                    question,
                    stock_name=stock_name,
                    stock_code=stock_code,
                )
            else:
                system_prompt, user_prompt = build_prompt(
                    "general",
                    question,
                    diagnosis_context=context,
                )

        answer = await _call_deepseek(system_prompt, user_prompt)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 问答服务异常: {str(e)[:100]}")

    return DiagnoseChatResponse(blocked=False, answer=answer, model="deepseek-chat")


@router.post("/chat", response_model=DiagnoseChatResponse)
async def diagnose_chat(body: DiagnoseChatRequest, db: Session = Depends(get_db)):
    return await chat_with_diagnose(body, db)
