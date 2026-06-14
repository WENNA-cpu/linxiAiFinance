import os
from typing import List, Dict, Any, Optional

import aiohttp

from app.core.env_loader import _BACKEND_DIR, _PROJECT_ROOT  # noqa: F401 — 确保 env 已加载

EDUCATION_SYSTEM_PROMPT = """你是一位专业的理财投教助手，服务于「灵析 AI 智能投顾助手」平台。

回答要求：
1. 用通俗易懂的中文解释投资概念，适合普通投资者阅读
2. 内容客观中立，不夸大收益，不做具体买卖建议
3. 适当举例帮助理解，回答简洁有条理（200-400字为宜）
4. 涉及风险时主动提示：历史收益不代表未来表现，投资有风险
5. 若问题与投资理财无关，礼貌说明并引导回到投教话题"""


def _get_deepseek_config() -> tuple[str, str, str]:
    """运行时读取 DeepSeek 配置，支持多种环境变量名"""
    api_key = (
        os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("DEEPSEEK_KEY")
        or os.getenv("DEEPSEEK_TOKEN")
        or ""
    ).strip()
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
    return api_key, base_url, model


async def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """调用 DeepSeek Chat Completions API（OpenAI 兼容格式）"""
    api_key, base_url, default_model = _get_deepseek_config()
    if not api_key:
        env_paths = f"{_BACKEND_DIR / '.env'} 或 {_PROJECT_ROOT / '.env'}"
        return {
            "error": f"未配置 DEEPSEEK_API_KEY，请在 {env_paths} 中添加后重启后端",
        }

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model or default_model,
        "messages": messages,
        "stream": False,
        "temperature": 0.7,
    }

    timeout_cfg = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                body = await response.json(content_type=None)
                if response.status != 200:
                    detail = body.get("error", {}).get("message") if isinstance(body, dict) else str(body)
                    return {"error": detail or f"DeepSeek API 错误 ({response.status})"}
                return body
        except aiohttp.ClientError as e:
            return {"error": f"网络请求失败: {e}"}
        except Exception as e:
            return {"error": str(e)}


async def answer_education_question(question: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """回答投教相关问题"""
    messages: List[Dict[str, str]] = [{"role": "system", "content": EDUCATION_SYSTEM_PROMPT}]

    if history:
        for item in history[-6:]:
            role = item.get("role")
            content = item.get("content", "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question.strip()})

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


GENERIC_STOCK_SYSTEM_PROMPT = """你是「灵析 AI 智能投顾助手」的投教解读助手。

回答要求：
1. 客观介绍公司或标的的基本面、主营业务、近期市场表现与估值概况
2. 严禁给出具体买卖建议、推荐买入卖出、承诺收益或预测涨跌
3. 说明该标的不在用户当前持仓中，介绍内容仅供参考，投资有风险
4. 回答简洁清晰，200-400字为宜，必要时使用条目列表"""


DIAGNOSE_FOLLOWUP_SYSTEM_PROMPT = """你是「灵析 AI 智能投顾助手」的持仓诊断解读助手。

回答要求：
1. 仅基于提供的完整持仓诊断结果进行客观解读，用户可能询问组合中任意一只资产
2. 若用户提到某只股票/基金名称，务必在「各资产明细」中查找对应数据后再回答，不要声称没有该资产数据
3. 严禁给出具体买卖建议、推荐具体标的、承诺收益或预测涨跌
4. 若用户询问「能买吗/能卖吗/何时卖」等，礼貌说明合规限制并引导其关注风险与长期规划
5. 回答简洁清晰，200-400字为宜，必要时使用条目列表"""


def _format_diagnosis_context(context: dict[str, Any]) -> str:
    assets = context.get("assets") or []
    summary = context.get("summary") or {}

    if assets or summary:
        lines: list[str] = []

        if summary:
            lines.append("【持仓组合概览】")
            total_assets = summary.get("total_assets")
            if total_assets is not None:
                lines.append(f"持仓数量：{total_assets} 只")
            total_change = summary.get("total_change")
            if total_change is not None:
                lines.append(f"组合持仓盈亏：{float(total_change):.2f}%")
            if summary.get("market_trend"):
                lines.append(f"市场趋势：{summary['market_trend']}")
            if summary.get("sector_rotation"):
                lines.append(f"板块轮动：{summary['sector_rotation']}")
            lines.append("")

        if assets:
            lines.append("【各资产明细】（以下为真实持仓诊断数据，请据此回答）")
            for idx, asset in enumerate(assets, 1):
                name = asset.get("name") or "未知"
                ts_code = asset.get("ts_code") or asset.get("code") or "-"
                risk = asset.get("risk_level") or "中"
                change_pct = asset.get("change_pct")
                change_text = f"{float(change_pct):.2f}%" if change_pct is not None else "暂无"
                parts = [f"{idx}. {name}（{ts_code}）", f"持仓盈亏 {change_text}", f"风险 {risk}"]
                if asset.get("today_change_pct") is not None:
                    parts.append(f"今日涨跌 {float(asset['today_change_pct']):.2f}%")
                if asset.get("cost_price") is not None:
                    parts.append(f"成本价 {float(asset['cost_price']):.2f}")
                if asset.get("current_price") is not None:
                    parts.append(f"当前价 {float(asset['current_price']):.2f}")
                if asset.get("quantity") is not None:
                    parts.append(f"数量 {float(asset['quantity']):.0f}")
                lines.append(" | ".join(parts))

        return "\n".join(lines)

    # 兼容旧版单资产上下文
    asset_name = context.get("asset_name") or "综合持仓"
    interval = context.get("interval") or "参见诊断结论"
    risk_level = context.get("risk_level") or "中"
    change_pct = context.get("change_pct")
    change_text = f"{change_pct:.2f}%" if change_pct is not None else "暂无"
    market_trend = context.get("market_trend") or ""
    sector_rotation = context.get("sector_rotation") or ""

    lines = [
        f"资产名称：{asset_name}",
        f"当前估值区间：{interval}",
        f"风险评级：{risk_level}",
        f"持仓盈亏：{change_text}",
    ]
    if market_trend:
        lines.append(f"市场趋势：{market_trend}")
    if sector_rotation:
        lines.append(f"板块轮动：{sector_rotation}")
    return "\n".join(lines)


async def answer_diagnose_followup(
    question: str,
    diagnosis_context: Dict[str, Any],
    focus_asset: Optional[Dict[str, Any]] = None,
) -> str:
    """基于诊断上下文的合规追问回答"""
    context_block = _format_diagnosis_context(diagnosis_context)
    focus_note = ""
    if focus_asset:
        name = focus_asset.get("name") or "该资产"
        ts_code = focus_asset.get("ts_code") or focus_asset.get("code") or ""
        code_part = f"（{ts_code}）" if ts_code else ""
        focus_note = f"\n用户本次询问的持仓资产：{name}{code_part}，请重点结合该资产在明细中的成本、盈亏与风险数据回答。\n"

    user_content = (
        f"用户持仓诊断结果：\n{context_block}\n"
        f"{focus_note}\n"
        f"用户问题：{question.strip()}\n\n"
        "请基于以上诊断结果回答，不要给出具体的买卖建议。"
    )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": DIAGNOSE_FOLLOWUP_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
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


async def answer_diagnose_external_stock(
    question: str,
    stock_name: str,
    stock_code: str = "",
) -> str:
    """非持仓标的的通用介绍模式（仍走 DeepSeek）"""
    code_part = f"（{stock_code}）" if stock_code else ""
    intro_request = (
        f"请介绍一下{stock_name}{code_part}这家公司，包括主营业务、近期走势、估值情况。"
        f"不要给出买卖建议。"
    )
    user_content = (
        f"{intro_request}\n\n"
        f"用户原始问题：{question.strip()}\n\n"
        "请注意：该标的不在用户当前持仓中，请基于公开信息客观介绍，不要给出具体的买卖建议。"
    )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": GENERIC_STOCK_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
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
