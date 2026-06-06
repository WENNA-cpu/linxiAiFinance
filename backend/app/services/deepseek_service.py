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
