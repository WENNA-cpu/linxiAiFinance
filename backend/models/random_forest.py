import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, mean_squared_error
import joblib
import os
import json


class RandomForestModel:
    """随机森林模型 - 用于风险评级和分类预测"""

    def __init__(self, task: str = "classification", model_path: str = None):
        self.task = task
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = model_path
        self.feature_names = []
        self.is_trained = False

        if model_path and os.path.exists(model_path):
            self._load_model()
        else:
            self._build_model()

    def _build_model(self):
        """构建模型"""
        if self.task == "classification":
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            )
        else:
            self.model = RandomForestRegressor(
                n_estimators=200,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            )

    def prepare_features(self, data: List[Dict[str, float]]) -> np.ndarray:
        """准备特征数据"""
        if not data:
            return np.array([])

        # 提取特征
        features = []
        for item in data:
            feature_vector = [
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
            features.append(feature_vector)

        return np.array(features)

    def train(self, X: np.ndarray, y: np.ndarray, validation_split: float = 0.2) -> Dict[str, Any]:
        """训练模型"""
        if len(X) < 10:
            return {"error": "训练数据不足，需要至少10条数据"}

        # 分割训练集和验证集
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42
        )

        # 标准化
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # 训练
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True

        # 验证
        predictions = self.model.predict(X_val_scaled)

        if self.task == "classification":
            accuracy = accuracy_score(y_val, predictions)
            # 交叉验证
            cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=5)
            metrics = {
                "accuracy": round(accuracy, 4),
                "cv_mean": round(cv_scores.mean(), 4),
                "cv_std": round(cv_scores.std(), 4),
            }
        else:
            mse = mean_squared_error(y_val, predictions)
            rmse = np.sqrt(mse)
            metrics = {
                "mse": round(mse, 4),
                "rmse": round(rmse, 4),
            }

        # 保存模型
        if self.model_path:
            self._save_model()

        return {
            "trained": True,
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "metrics": metrics,
            "feature_importance": self.feature_importance(),
        }

    def predict(self, X: np.ndarray) -> Any:
        """预测"""
        if not self.is_trained:
            return None
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """预测概率"""
        if not self.is_trained or self.task != "classification":
            return np.array([])
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def feature_importance(self) -> Dict[str, float]:
        """特征重要性"""
        if not hasattr(self.model, "feature_importances_"):
            return {}

        feature_names = [
            "concentration", "volatility", "liquidity", "leverage",
            "beta", "sharpe_ratio", "max_drawdown", "var_95",
            "correlation", "momentum"
        ]

        importances = self.model.feature_importances_
        return {
            name: round(float(importance), 4)
            for name, importance in zip(feature_names[:len(importances)], importances)
        }

    def _save_model(self):
        """保存模型"""
        if not self.model_path:
            return

        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        # 保存模型和scaler
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "task": self.task,
            "is_trained": self.is_trained,
        }, self.model_path)

        # 保存元数据
        meta_path = self.model_path.replace('.pkl', '_meta.json')
        with open(meta_path, 'w') as f:
            json.dump({
                "task": self.task,
                "is_trained": self.is_trained,
                "feature_importance": self.feature_importance(),
            }, f)

    def _load_model(self):
        """加载模型"""
        try:
            data = joblib.load(self.model_path)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.task = data.get("task", "classification")
            self.is_trained = data.get("is_trained", True)
        except Exception as e:
            print(f"Error loading model: {e}")
            self._build_model()


class RiskRatingModel(RandomForestModel):
    """风险评级模型 - 专门用于投资组合风险评估"""

    def __init__(self, model_path: str = "backend/models/saved/risk_model.pkl"):
        super().__init__(task="classification", model_path=model_path)
        self.risk_levels = ["低风险", "中低风险", "中风险", "中高风险", "高风险"]

    def calculate_risk_features(self, portfolio_data: Dict[str, Any]) -> Dict[str, float]:
        """计算风险特征"""
        assets = portfolio_data.get("assets", [])
        if not assets:
            return {}

        # 计算集中度
        weights = [asset.get("weight", 0) for asset in assets]
        concentration = max(weights) if weights else 0

        # 计算波动率（模拟）
        volatilities = [asset.get("volatility", 0.2) for asset in assets]
        avg_volatility = np.mean(volatilities) if volatilities else 0.2

        # 计算流动性
        liquidities = [asset.get("liquidity", 1.0) for asset in assets]
        avg_liquidity = np.mean(liquidities) if liquidities else 1.0

        # 杠杆率
        leverage = portfolio_data.get("leverage", 1.0)

        # Beta系数
        betas = [asset.get("beta", 1.0) for asset in assets]
        avg_beta = np.mean(betas) if betas else 1.0

        # 夏普比率
        sharpes = [asset.get("sharpe_ratio", 0) for asset in assets]
        avg_sharpe = np.mean(sharpes) if sharpes else 0

        # 最大回撤
        drawdowns = [asset.get("max_drawdown", 0.1) for asset in assets]
        avg_drawdown = np.mean(drawdowns) if drawdowns else 0.1

        # VaR
        var_values = [asset.get("var_95", 0.05) for asset in assets]
        avg_var = np.mean(var_values) if var_values else 0.05

        # 相关性
        correlations = [asset.get("correlation", 0.5) for asset in assets]
        avg_correlation = np.mean(correlations) if correlations else 0.5

        # 动量
        momentums = [asset.get("momentum", 0) for asset in assets]
        avg_momentum = np.mean(momentums) if momentums else 0

        return {
            "concentration": concentration,
            "volatility": avg_volatility,
            "liquidity": avg_liquidity,
            "leverage": leverage,
            "beta": avg_beta,
            "sharpe_ratio": avg_sharpe,
            "max_drawdown": avg_drawdown,
            "var_95": avg_var,
            "correlation": avg_correlation,
            "momentum": avg_momentum,
        }

    def rate_portfolio(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估投资组合风险"""
        features = self.calculate_risk_features(portfolio_data)

        if not features:
            return {
                "risk_level": "未知",
                "risk_score": 50,
                "confidence": 0,
                "factors": {},
            }

        # 准备特征向量
        X = np.array([[
            features.get("concentration", 0),
            features.get("volatility", 0),
            features.get("liquidity", 0),
            features.get("leverage", 0),
            features.get("beta", 0),
            features.get("sharpe_ratio", 0),
            features.get("max_drawdown", 0),
            features.get("var_95", 0),
            features.get("correlation", 0),
            features.get("momentum", 0),
        ]])

        if self.is_trained:
            # 使用训练好的模型预测
            risk_level_idx = self.predict(X)[0]
            probabilities = self.predict_proba(X)[0]
            confidence = float(max(probabilities))
            risk_level = self.risk_levels[risk_level_idx] if isinstance(risk_level_idx, int) and 0 <= risk_level_idx < len(self.risk_levels) else "中风险"
        else:
            # 使用规则计算风险评分
            risk_score = self._calculate_rule_based_score(features)
            risk_level = self._score_to_level(risk_score)
            confidence = 0.7

        # 计算风险评分 (0-100)
        risk_score = self._calculate_risk_score(features)

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "confidence": round(confidence, 2),
            "factors": features,
            "warnings": self._generate_warnings(features),
            "suggestions": self._generate_suggestions(features),
        }

    def _calculate_rule_based_score(self, features: Dict[str, float]) -> int:
        """基于规则计算风险评分"""
        score = 50

        # 集中度风险
        if features.get("concentration", 0) > 0.5:
            score += 15
        elif features.get("concentration", 0) > 0.3:
            score += 5

        # 波动率风险
        if features.get("volatility", 0) > 0.3:
            score += 10

        # 杠杆风险
        if features.get("leverage", 1) > 2:
            score += 15
        elif features.get("leverage", 1) > 1.5:
            score += 5

        # Beta风险
        if features.get("beta", 1) > 1.5:
            score += 10

        # 回撤风险
        if features.get("max_drawdown", 0) > 0.2:
            score += 10

        return min(100, max(0, score))

    def _calculate_risk_score(self, features: Dict[str, float]) -> int:
        """计算综合风险评分"""
        weights = {
            "concentration": 0.25,
            "volatility": 0.20,
            "leverage": 0.15,
            "beta": 0.15,
            "max_drawdown": 0.15,
            "var_95": 0.10,
        }

        score = 0
        for factor, weight in weights.items():
            value = features.get(factor, 0)
            # 归一化到0-100
            if factor == "concentration":
                normalized = value * 100
            elif factor == "volatility":
                normalized = value * 100
            elif factor == "leverage":
                normalized = (value - 1) * 50
            elif factor == "beta":
                normalized = max(0, (value - 0.5) * 50)
            elif factor == "max_drawdown":
                normalized = value * 100
            elif factor == "var_95":
                normalized = value * 100
            else:
                normalized = value * 50

            score += min(100, normalized) * weight

        return int(min(100, max(0, score)))

    def _score_to_level(self, score: int) -> str:
        """评分转风险等级"""
        if score < 20:
            return "低风险"
        elif score < 40:
            return "中低风险"
        elif score < 60:
            return "中风险"
        elif score < 80:
            return "中高风险"
        else:
            return "高风险"

    def _generate_warnings(self, features: Dict[str, float]) -> List[str]:
        """生成风险提示"""
        warnings = []

        if features.get("concentration", 0) > 0.5:
            warnings.append("持仓集中度偏高，建议分散投资")

        if features.get("volatility", 0) > 0.3:
            warnings.append("组合波动率较高，注意风险控制")

        if features.get("leverage", 1) > 1.5:
            warnings.append("使用杠杆交易，风险放大")

        if features.get("max_drawdown", 0) > 0.2:
            warnings.append("历史回撤较大，需关注下行风险")

        if features.get("beta", 1) > 1.5:
            warnings.append("Beta系数较高，市场敏感性强")

        return warnings

    def _generate_suggestions(self, features: Dict[str, float]) -> List[str]:
        """生成优化建议"""
        suggestions = []

        if features.get("concentration", 0) > 0.4:
            suggestions.append("考虑增加持仓数量，降低单一资产占比")

        if features.get("sharpe_ratio", 0) < 0.5:
            suggestions.append("风险调整后收益偏低，可优化资产配置")

        if features.get("correlation", 0) > 0.8:
            suggestions.append("资产间相关性较高，建议增加低相关资产")

        if features.get("liquidity", 1) < 0.5:
            suggestions.append("部分资产流动性不足，注意变现风险")

        return suggestions


class ReturnPredictionModel(RandomForestModel):
    """收益预测模型 - 用于预测资产收益"""

    def __init__(self, model_path: str = "backend/models/saved/return_model.pkl"):
        super().__init__(task="regression", model_path=model_path)

    def prepare_features(self, data: List[Dict[str, float]]) -> np.ndarray:
        """准备特征数据"""
        features = []
        for item in data:
            feature_vector = [
                item.get("pe", 0),
                item.get("pb", 0),
                item.get("ps", 0),
                item.get("roe", 0),
                item.get("roa", 0),
                item.get("revenue_growth", 0),
                item.get("profit_growth", 0),
                item.get("debt_ratio", 0),
                item.get("current_ratio", 0),
                item.get("momentum_1m", 0),
                item.get("momentum_3m", 0),
                item.get("volatility", 0),
            ]
            features.append(feature_vector)

        return np.array(features)

    def predict_return(self, asset_features: Dict[str, float]) -> Dict[str, Any]:
        """预测收益"""
        X = np.array([[
            asset_features.get("pe", 0),
            asset_features.get("pb", 0),
            asset_features.get("ps", 0),
            asset_features.get("roe", 0),
            asset_features.get("roa", 0),
            asset_features.get("revenue_growth", 0),
            asset_features.get("profit_growth", 0),
            asset_features.get("debt_ratio", 0),
            asset_features.get("current_ratio", 0),
            asset_features.get("momentum_1m", 0),
            asset_features.get("momentum_3m", 0),
            asset_features.get("volatility", 0),
        ]])

        if self.is_trained:
            predicted_return = self.predict(X)[0]
            # 计算置信区间
            predictions = []
            for estimator in self.model.estimators_:
                pred = estimator.predict(self.scaler.transform(X))[0]
                predictions.append(pred)
            std = np.std(predictions)
        else:
            # 基于规则预测
            predicted_return = self._rule_based_prediction(asset_features)
            std = 0.05

        return {
            "predicted_return_1m": round(predicted_return, 4),
            "confidence_interval": {
                "lower": round(predicted_return - 2 * std, 4),
                "upper": round(predicted_return + 2 * std, 4),
            },
            "confidence": round(1 - min(std * 10, 0.5), 2),
        }

    def _rule_based_prediction(self, features: Dict[str, float]) -> float:
        """基于规则的收益预测"""
        score = 0

        # PE估值
        pe = features.get("pe", 15)
        if pe < 10:
            score += 0.02
        elif pe > 30:
            score -= 0.01

        # PB估值
        pb = features.get("pb", 1.5)
        if pb < 1:
            score += 0.015
        elif pb > 3:
            score -= 0.01

        # ROE
        roe = features.get("roe", 0.1)
        score += roe * 0.1

        # 营收增长
        growth = features.get("revenue_growth", 0.1)
        score += growth * 0.05

        # 动量
        momentum = features.get("momentum_1m", 0)
        score += momentum * 0.3

        return score
