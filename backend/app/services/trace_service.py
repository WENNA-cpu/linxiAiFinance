from typing import Any, Dict, List, Optional


def _categorize_step(step_name: str) -> str:
    if any(k in step_name for k in ("数据获取", "Tushare", "行情", "持仓")):
        return "数据源"
    if any(k in step_name for k in ("清洗", "加密", "转换")):
        return "处理"
    if any(k in step_name for k in ("LSTM", "随机森林", "模型", "情绪", "预测")):
        return "模型"
    if any(k in step_name for k in ("规则", "校验", "风控")):
        return "处理"
    if any(k in step_name for k in ("结果", "输出", "生成")):
        return "输出"
    return "处理"


def build_lineage_from_logs(logs: List[Any]) -> Dict[str, Any]:
    """根据审计日志构建数据血缘图"""
    if not logs:
        return {"nodes": [], "links": []}

    nodes: List[Dict[str, str]] = []
    node_names: set = set()

    for log in logs:
        name = log.step_name
        if name not in node_names:
            nodes.append({"name": name, "category": _categorize_step(name)})
            node_names.add(name)

        detail = log.step_detail or ""
        if "Tushare" in detail and "Tushare行情数据" not in node_names:
            nodes.insert(0, {"name": "Tushare行情数据", "category": "数据源"})
            node_names.add("Tushare行情数据")
        if "持仓" in detail and "用户持仓数据" not in node_names:
            nodes.append({"name": "用户持仓数据", "category": "数据源"})
            node_names.add("用户持仓数据")

    ordered_steps: List[str] = []
    for log in logs:
        if not ordered_steps or ordered_steps[-1] != log.step_name:
            ordered_steps.append(log.step_name)

    links: List[Dict[str, str]] = []
    for i in range(len(ordered_steps) - 1):
        link = {"source": ordered_steps[i], "target": ordered_steps[i + 1]}
        if link not in links:
            links.append(link)

    if "Tushare行情数据" in node_names and ordered_steps:
        links.insert(0, {"source": "Tushare行情数据", "target": ordered_steps[0]})

    output_node = next((n for n in nodes if n["category"] == "输出"), None)
    model_nodes = [n["name"] for n in nodes if n["category"] == "模型"]
    if output_node and model_nodes:
        for model in model_nodes:
            link = {"source": model, "target": output_node["name"]}
            if link not in links:
                links.append(link)

    return {"nodes": nodes, "links": links}
