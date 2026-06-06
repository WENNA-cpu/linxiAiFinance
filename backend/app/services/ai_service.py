import uuid
from datetime import datetime
from typing import Dict, Any, List
import os
import sys

# 添加模型目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from models.lstm_model import LSTMModel, CycleAnalyzer
from models.random_forest import RiskRatingModel, ReturnPredictionModel
from app.services.data_service import DataService


class AIService:
    """AI服务封装 - 整合模型和数据服务"""

    def __init__(self):
        self.data_service = DataService()
        self.cycle_analyzer = CycleAnalyzer()
        self.risk_model = RiskRatingModel()
        self.return_model = ReturnPredictionModel()

    async def diagnose_portfolio(self, request_id: str, portfolio_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """持仓诊断 - 整合风险评级和收益预测"""
        if portfolio_data is None:
            portfolio_data = self._get_mock_portfolio()

        # 风险评级
        risk_assessment = self.risk_model.rate_portfolio(portfolio_data)

        # 获取市场数据
        market_sentiment = await self.data_service.fetch_sentiment_data()

        # 分析持仓资产
        asset_analysis = await self._analyze_assets(portfolio_data.get("assets", []))

        return {
            "request_id": request_id,
            "confidence": risk_assessment.get("confidence", 0.7) * 100,
            "summary": {
                "total_assets": len(portfolio_data.get("assets", [])),
                "risk_assets": len([a for a in asset_analysis if a.get("risk_level") in ["中高风险", "高风险"]]),
                "opportunity_assets": len([a for a in asset_analysis if a.get("opportunity_score", 0) > 70]),
                "time_saved": 45,
            },
            "risk_assessment": risk_assessment,
            "market_context": market_sentiment,
            "asset_analysis": asset_analysis,
            "analysis": {
                "market_trend": self._generate_market_comment(market_sentiment),
                "sector_rotation": "近期市场风格切换较快，建议关注估值合理的优质资产",
                "risk_points": risk_assessment.get("warnings", []),
                "opportunities": self._generate_opportunities(asset_analysis),
            },
            "data_source": {
                "time_range": "2024-01-01 至 2024-01-15",
                "sources": ["Tushare行情数据", "行业研报数据", "资金流向数据"],
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        }

    async def analyze_cycle(self, asset_code: str, time_range: str = "1y") -> Dict[str, Any]:
        """资产周期分析 - 使用LSTM模型"""
        # 获取历史数据
        market_data = await self.data_service.fetch_market_data(asset_code)

        if not market_data:
            # 返回模拟数据
            return {
                "asset_code": asset_code,
                "current_phase": "合理区间",
                "valuation": {
                    "pe": 8.5,
                    "pb": 0.85,
                    "pe_percentile": 45,
                    "pb_percentile": 38,
                },
                "recommendation": "持有观望",
                "confidence": 78,
                "lstm_forecast": {
                    "trend": "震荡",
                    "confidence": 72,
                    "support": 12.5,
                    "resistance": 15.8,
                },
            }

        # 提取价格数据
        history = market_data.get("history", [])
        prices = [h.get("close", 0) for h in history if h.get("close")]

        # 使用LSTM分析
        if len(prices) >= 60:
            analysis = self.cycle_analyzer.lstm_model.analyze_cycle(prices)
            prediction = analysis.get("prediction", {})

            return {
                "asset_code": asset_code,
                "current_phase": analysis.get("current_phase", "合理区间"),
                "valuation": market_data.get("valuation", {}),
                "recommendation": analysis.get("recommendation", "持有观望"),
                "confidence": prediction.get("confidence", 70),
                "lstm_forecast": {
                    "trend": prediction.get("trend", "震荡"),
                    "confidence": prediction.get("confidence", 70),
                    "support": prediction.get("support", 0),
                    "resistance": prediction.get("resistance", 0),
                    "predicted_value": prediction.get("predicted_value", 0),
                },
                "statistics": analysis.get("statistics", {}),
            }
        else:
            return {
                "asset_code": asset_code,
                "current_phase": "数据不足",
                "valuation": market_data.get("valuation", {}),
                "recommendation": "数据不足，无法分析",
                "confidence": 0,
                "lstm_forecast": {},
            }

    async def predict_returns(self, asset_code: str) -> Dict[str, Any]:
        """预测资产收益"""
        # 获取估值数据
        valuation = await self.data_service.fetch_valuation_data(asset_code)

        # 构建特征
        features = {
            "pe": valuation.get("pe", 15),
            "pb": valuation.get("pb", 1.5),
            "ps": valuation.get("ps", 2),
            "roe": 0.12,
            "roa": 0.08,
            "revenue_growth": 0.15,
            "profit_growth": 0.12,
            "debt_ratio": 0.4,
            "current_ratio": 1.5,
            "momentum_1m": 0.02,
            "momentum_3m": 0.05,
            "volatility": 0.25,
        }

        prediction = self.return_model.predict_return(features)

        return {
            "asset_code": asset_code,
            "prediction": prediction,
            "features": features,
        }

    async def generate_education_content(self, asset_type: str) -> Dict[str, Any]:
        """生成投教内容"""
        content_map = {
            "stock": {
                "title": "股票投资基础",
                "content": "股票是最常见的权益类资产，代表对公司的所有权。投资股票需要关注公司基本面、行业前景和估值水平。",
                "courses": [
                    {"id": 1, "title": "股票估值基础：PE、PB、PS详解", "level": "入门", "duration": "30分钟"},
                    {"id": 2, "title": "技术分析入门：K线与趋势线", "level": "入门", "duration": "45分钟"},
                    {"id": 3, "title": "基本面分析：如何读财报", "level": "进阶", "duration": "60分钟"},
                ],
            },
            "fund": {
                "title": "基金投资指南",
                "content": "基金是一种集合投资工具，由专业基金经理管理。适合没有时间研究个股的投资者。",
                "courses": [
                    {"id": 1, "title": "基金分类：股票型、债券型、混合型", "level": "入门", "duration": "25分钟"},
                    {"id": 2, "title": "定投策略：微笑曲线原理", "level": "进阶", "duration": "40分钟"},
                    {"id": 3, "title": "基金筛选：看这些指标就够了", "level": "进阶", "duration": "50分钟"},
                ],
            },
            "bond": {
                "title": "债券投资入门",
                "content": "债券是固定收益类资产，风险相对较低。适合保守型投资者作为资产配置的一部分。",
                "courses": [
                    {"id": 1, "title": "债券基础：收益率与价格关系", "level": "入门", "duration": "35分钟"},
                    {"id": 2, "title": "利率风险：久期概念解析", "level": "进阶", "duration": "45分钟"},
                ],
            },
        }

        default_content = {
            "title": "理财知识库",
            "content": "基于您的持仓类型，为您推荐相关理财知识。",
            "courses": [
                {"id": 1, "title": "资产配置基础", "level": "入门", "duration": "30分钟"},
                {"id": 2, "title": "风险管理原则", "level": "入门", "duration": "25分钟"},
            ],
        }

        return content_map.get(asset_type, default_content)

    async def _analyze_assets(self, assets: List[Dict]) -> List[Dict]:
        """分析单个资产"""
        results = []
        for asset in assets:
            code = asset.get("code", "")

            # 获取市场数据
            market_data = await self.data_service.fetch_market_data(code)

            if market_data:
                valuation = market_data.get("valuation", {})
                pe = valuation.get("pe", 0)
                pb = valuation.get("pb", 0)

                # 简单估值判断
                if pe > 0 and pe < 15:
                    valuation_status = "低估"
                    opportunity_score = 80
                elif pe > 0 and pe < 30:
                    valuation_status = "合理"
                    opportunity_score = 60
                else:
                    valuation_status = "偏高"
                    opportunity_score = 40

                results.append({
                    "code": code,
                    "name": asset.get("name", ""),
                    "weight": asset.get("weight", 0),
                    "risk_level": asset.get("risk_level", "中"),
                    "valuation_status": valuation_status,
                    "pe": pe,
                    "pb": pb,
                    "opportunity_score": opportunity_score,
                    "current_price": market_data.get("close", 0),
                    "change_pct": market_data.get("pct_chg", 0),
                })
            else:
                results.append({
                    "code": code,
                    "name": asset.get("name", ""),
                    "weight": asset.get("weight", 0),
                    "risk_level": asset.get("risk_level", "中"),
                    "valuation_status": "未知",
                    "opportunity_score": 50,
                })

        return results

    def _get_mock_portfolio(self) -> Dict[str, Any]:
        """获取模拟持仓数据"""
        return {
            "assets": [
                {"code": "000001.SZ", "name": "平安银行", "weight": 0.25, "risk_level": "中", "volatility": 0.25},
                {"code": "000002.SZ", "name": "万科A", "weight": 0.20, "risk_level": "中高", "volatility": 0.30},
                {"code": "000858.SZ", "name": "五粮液", "weight": 0.30, "risk_level": "中", "volatility": 0.28},
                {"code": "002415.SZ", "name": "海康威视", "weight": 0.25, "risk_level": "中", "volatility": 0.26},
            ],
            "leverage": 1.0,
        }

    def _generate_market_comment(self, sentiment: Dict) -> str:
        """生成市场评论"""
        status = sentiment.get("status", "中性")
        index = sentiment.get("index", 50)

        if index > 70:
            return f"当前市场情绪{status}，整体估值处于历史较高水平，建议保持谨慎。"
        elif index < 30:
            return f"当前市场情绪{status}，整体估值处于历史较低水平，可能存在配置机会。"
        else:
            return f"当前市场情绪{status}，整体估值处于历史中等水平，建议精选个股。"

    def _generate_opportunities(self, asset_analysis: List[Dict]) -> List[str]:
        """生成机会列表"""
        opportunities = []

        undervalued = [a for a in asset_analysis if a.get("valuation_status") == "低估"]
        if undervalued:
            names = ", ".join([a.get("name", "") for a in undervalued[:2]])
            opportunities.append(f"{names}等资产估值处于低位，具备中长期配置价值")

        high_opportunity = [a for a in asset_analysis if a.get("opportunity_score", 0) > 70]
        if high_opportunity:
            opportunities.append("部分持仓资产基本面良好，建议继续持有")

        if not opportunities:
            opportunities.append("建议关注低估值蓝筹和业绩稳健的消费板块")

        return opportunities


class ModelTrainingService:
    """模型训练服务"""

    def __init__(self):
        self.data_service = DataService()

    async def train_lstm_model(self, ts_code: str, epochs: int = 50) -> Dict[str, Any]:
        """训练LSTM模型"""
        # 获取历史数据
        market_data = await self.data_service.fetch_daily_data(ts_code)

        if not market_data or len(market_data) < 100:
            return {"error": "数据不足，无法训练模型"}

        # 提取收盘价
        prices = [float(d.get("close", 0)) for d in market_data if d.get("close")]

        if len(prices) < 100:
            return {"error": "价格数据不足"}

        # 训练模型
        model = LSTMModel(sequence_length=60)
        result = model.train(prices, epochs=epochs)

        return {
            "model_type": "LSTM",
            "asset_code": ts_code,
            "training_result": result,
            "data_points": len(prices),
        }

    async def train_risk_model(self, training_data: List[Dict]) -> Dict[str, Any]:
        """训练风险评级模型"""
        if len(training_data) < 20:
            return {"error": "训练数据不足，需要至少20条数据"}

        # 准备特征和标签
        X = []
        y = []

        for item in training_data:
            features = [
                item.get("concentration", 0),
                item.get("volatility", 0),
                item.get("liquidity", 0),
                item.get("leverage", 0),
                item.get("beta", 0),
                item.get("sharpe_ratio", 0),
                item.get("max_drawdown", 0),
                item.get("var_95", 0),
                item.get("correlation", 0),
                item.get("momentum", 0),
            ]
            X.append(features)

            # 风险等级映射
            risk_level = item.get("risk_level", "中")
            level_map = {"低": 0, "中低": 1, "中": 2, "中高": 3, "高": 4}
            y.append(level_map.get(risk_level, 2))

        import numpy as np
        X = np.array(X)
        y = np.array(y)

        # 训练模型
        model = RiskRatingModel()
        result = model.train(X, y)

        return {
            "model_type": "RandomForest",
            "task": "classification",
            "training_result": result,
        }
