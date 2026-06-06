import re
from typing import Dict, Any, List


class RiskControlService:
    """风控规则服务"""

    FORBIDDEN_WORDS = [
        "荐股", "保证收益", "稳赚", "翻倍", "内幕消息",
        "涨停", "抄底", "买入信号", "必涨", "包赚",
        "一定涨", "肯定赚", "绝对赚", "稳赢", "零风险",
    ]

    def __init__(self):
        self.forbidden_pattern = re.compile("|".join(self.FORBIDDEN_WORDS))

    def filter_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """过滤AI输出"""
        output_text = str(output)

        if self.forbidden_pattern.search(output_text):
            output["warning"] = "内容包含敏感词汇，已进行合规处理"
            output["confidence"] = min(output.get("confidence", 100) * 0.8, 70)

        output = self._validate_numbers(output)
        output = self._add_disclaimer(output)

        return output

    def _validate_numbers(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """数值校验"""
        if "valuation" in output:
            valuation = output["valuation"]
            if "pe" in valuation:
                pe = valuation["pe"]
                if pe < 0 or pe > 100:
                    output["warning"] = "市盈率数据异常，请谨慎参考"

        return output

    def _add_disclaimer(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """添加免责声明"""
        output["disclaimer"] = "本内容仅为投资参考，不构成任何投资建议"
        return output

    def check_data_anomaly(self, data: Dict[str, Any]) -> List[str]:
        """检查数据异常"""
        anomalies = []

        if "change_percent" in data:
            change = abs(data["change_percent"])
            if change > 20:
                anomalies.append(f"涨跌幅异常: {change}%")

        return anomalies
