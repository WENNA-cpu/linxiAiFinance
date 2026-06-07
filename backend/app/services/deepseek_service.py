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


DIAGNOSE_FOLLOWUP_SYSTEM_PROMPT = """你是「灵析 AI 智能投顾助手」的持仓诊断解读助手。

回答要求：
1. 仅基于提供的诊断结果进行客观解读，帮助用户理解风险与估值状态
2. 严禁给出具体买卖建议、推荐具体标的、承诺收益或预测涨跌
3. 若用户询问「能买吗/能卖吗/何时卖」等，礼貌说明合规限制并引导其关注风险与长期规划
4. 回答简洁清晰，200-400字为宜，必要时使用条目列表"""


def _format_diagnosis_context(context: Dict[str, Any]) -> str:
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
        f"涨跌幅：{change_text}",
    ]
    if market_trend:
        lines.append(f"市场趋势：{market_trend}")
    if sector_rotation:
        lines.append(f"板块轮动：{sector_rotation}")
    return "\n".join(lines)


async def answer_diagnose_followup(question: str, diagnosis_context: Dict[str, Any]) -> str:
    """基于诊断上下文的合规追问回答"""
    context_block = _format_diagnosis_context(diagnosis_context)
    user_content = (
        f"用户持仓诊断结果：\n{context_block}\n\n"
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
