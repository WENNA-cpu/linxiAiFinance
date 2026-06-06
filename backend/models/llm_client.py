import os
import aiohttp
from typing import List, Dict, Any, Optional


class LLMClient:
    """LLM客户端"""

    def __init__(self):
        self.api_key = os.getenv("MEOO_PROJECT_API_KEY", "")
        self.base_url = "https://api.meoo.host"
        self.model = "qwen3.6-plus"

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """聊天完成"""
        url = f"{self.base_url}/meoo-ai/compatible-mode/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": stream,
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"API返回错误: {response.status}"}
            except Exception as e:
                return {"error": str(e)}

    async def analyze_portfolio(self, portfolio_data: Dict[str, Any]) -> str:
        """分析持仓"""
        system_prompt = """你是一位专业的投资顾问。请基于提供的持仓数据进行分析，给出客观、专业的见解。
注意：
1. 不做具体买卖建议
2. 不预测未来走势
3. 只基于历史数据做分析
4. 提示风险但不制造恐慌"""

        user_prompt = f"""请分析以下持仓数据：
总资产数: {portfolio_data.get('total_assets', 0)}
总市值: {portfolio_data.get('total_value', 0)}
请从风险、机会、行业分布等角度进行分析。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.chat_completion(messages)

        if "error" in response:
            return f"分析服务暂时不可用: {response['error']}"

        choices = response.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")

        return "无法生成分析结果"

    async def generate_education_content(self, topic: str, level: str = "入门") -> str:
        """生成投教内容"""
        system_prompt = """你是一位理财教育专家。请生成专业、易懂的投资教育内容。
内容要求：
1. 客观中立，不夸大收益
2. 风险提示充分
3. 适合指定水平的投资者"""

        user_prompt = f"请生成关于'{topic}'的{level}级别投教内容。"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.chat_completion(messages)

        if "error" in response:
            return f"内容生成失败: {response['error']}"

        choices = response.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")

        return "无法生成内容"
