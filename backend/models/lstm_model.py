import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import os
import json


class LSTMModel:
    """LSTM时序预测模型 - 用于资产周期分析"""

    def __init__(self, sequence_length: int = 60, model_path: str = None):
        self.sequence_length = sequence_length
        self.model = None
        self.model_path = model_path or "backend/models/saved/lstm_model.h5"
        self.scaler_params = {"mean": 0, "std": 1}

        # 创建保存目录
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

        # 尝试加载已有模型
        if os.path.exists(self.model_path):
            self._load_model()
        else:
            self._build_model()

    def _build_model(self):
        """构建LSTM模型"""
        self.model = Sequential([
            LSTM(128, return_sequences=True, input_shape=(self.sequence_length, 1)),
            Dropout(0.2),
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1),
        ])
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="mean_squared_error",
            metrics=['mae']
        )

    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """数据归一化"""
        self.scaler_params["mean"] = np.mean(data)
        self.scaler_params["std"] = np.std(data) if np.std(data) > 0 else 1
        return (data - self.scaler_params["mean"]) / self.scaler_params["std"]

    def _denormalize(self, data: np.ndarray) -> np.ndarray:
        """数据反归一化"""
        return data * self.scaler_params["std"] + self.scaler_params["mean"]

    def prepare_data(self, data: List[float]) -> tuple:
        """准备训练数据"""
        if len(data) < self.sequence_length + 1:
            return None, None

        x, y = [], []
        for i in range(self.sequence_length, len(data)):
            x.append(data[i - self.sequence_length:i])
            y.append(data[i])

        x = np.array(x)
        y = np.array(y)

        # 归一化
        x_normalized = self._normalize(x)
        y_normalized = self._normalize(y)

        return x_normalized, y_normalized

    def train(self, data: List[float], epochs: int = 50, validation_split: float = 0.2) -> Dict[str, Any]:
        """训练模型"""
        prepared = self.prepare_data(data)
        if prepared[0] is None:
            return {"error": "数据不足，需要至少 {} 条数据".format(self.sequence_length + 1)}

        x, y = prepared
        x = np.reshape(x, (x.shape[0], x.shape[1], 1))

        # 早停和模型检查点
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
            ModelCheckpoint(self.model_path, monitor='val_loss', save_best_only=True, verbose=0)
        ]

        history = self.model.fit(
            x, y,
            epochs=epochs,
            batch_size=32,
            validation_split=validation_split,
            callbacks=callbacks,
            verbose=0
        )

        # 保存归一化参数
        scaler_path = self.model_path.replace('.h5', '_scaler.json')
        with open(scaler_path, 'w') as f:
            json.dump(self.scaler_params, f)

        return {
            "epochs_trained": len(history.history['loss']),
            "final_loss": float(history.history['loss'][-1]),
            "final_val_loss": float(history.history['val_loss'][-1]),
            "model_saved": True,
        }

    def _load_model(self):
        """加载已保存的模型"""
        try:
            self.model = load_model(self.model_path)
            # 加载归一化参数
            scaler_path = self.model_path.replace('.h5', '_scaler.json')
            if os.path.exists(scaler_path):
                with open(scaler_path, 'r') as f:
                    self.scaler_params = json.load(f)
        except Exception as e:
            print(f"Error loading model: {e}")
            self._build_model()

    def predict(self, data: List[float]) -> Dict[str, Any]:
        """预测下一个值"""
        if len(data) < self.sequence_length:
            return {"error": "数据不足，需要至少 {} 条数据".format(self.sequence_length)}

        last_sequence = np.array(data[-self.sequence_length:])
        last_sequence_normalized = self._normalize(last_sequence)
        last_sequence_normalized = np.reshape(
            last_sequence_normalized,
            (1, self.sequence_length, 1)
        )

        prediction_normalized = self.model.predict(last_sequence_normalized, verbose=0)
        prediction = self._denormalize(prediction_normalized)

        current = data[-1]
        predicted = float(prediction[0][0])

        return {
            "predicted_value": predicted,
            "current_value": current,
            "change": round(predicted - current, 2),
            "change_pct": round((predicted - current) / current * 100, 2) if current > 0 else 0,
            "trend": "up" if predicted > current else "down",
        }

    def predict_with_confidence(self, data: List[float]) -> Dict[str, Any]:
        """带置信区间的预测"""
        prediction = self.predict(data)

        if "error" in prediction:
            return prediction

        current = data[-1] if data else 0
        predicted = prediction.get("predicted_value", current)

        # 计算波动率
        volatility = np.std(data[-30:]) if len(data) >= 30 else current * 0.05

        # 计算置信度 (基于模型预测稳定性和数据波动)
        confidence = self._calculate_confidence(data, predicted)

        return {
            "predicted_value": round(predicted, 2),
            "current_value": current,
            "confidence": confidence,
            "trend": prediction.get("trend", "neutral"),
            "support": round(predicted - 2 * volatility, 2),
            "resistance": round(predicted + 2 * volatility, 2),
            "forecast_range": {
                "low": round(predicted - volatility, 2),
                "high": round(predicted + volatility, 2),
            },
        }

    def _calculate_confidence(self, data: List[float], prediction: float) -> float:
        """计算预测置信度"""
        if len(data) < 10:
            return 50.0

        # 基于数据稳定性计算
        recent_data = data[-30:] if len(data) >= 30 else data
        volatility = np.std(recent_data) / np.mean(recent_data) if np.mean(recent_data) > 0 else 0

        # 波动率越低，置信度越高
        confidence = max(30, min(95, 100 - volatility * 100))
        return round(confidence, 1)

    def analyze_cycle(self, data: List[float]) -> Dict[str, Any]:
        """分析周期阶段"""
        if len(data) < self.sequence_length:
            return {"error": "数据不足"}

        # 计算估值百分位
        current = data[-1]
        min_val = min(data)
        max_val = max(data)
        percentile = (current - min_val) / (max_val - min_val) * 100 if max_val > min_val else 50

        # 预测
        prediction = self.predict_with_confidence(data)

        # 判断周期阶段
        if percentile < 20:
            phase = "低估区间"
            recommendation = "积极配置"
        elif percentile < 40:
            phase = "合理偏低"
            recommendation = "适度配置"
        elif percentile < 60:
            phase = "合理区间"
            recommendation = "持有观望"
        elif percentile < 80:
            phase = "合理偏高"
            recommendation = "谨慎持有"
        else:
            phase = "高估区间"
            recommendation = "考虑减仓"

        return {
            "current_phase": phase,
            "recommendation": recommendation,
            "percentile": round(percentile, 1),
            "current_value": current,
            "prediction": prediction,
            "statistics": {
                "min": round(min_val, 2),
                "max": round(max_val, 2),
                "mean": round(np.mean(data), 2),
                "std": round(np.std(data), 2),
            },
        }


class CycleAnalyzer:
    """周期分析器 - 整合多种分析方法"""

    def __init__(self):
        self.lstm_model = LSTMModel()

    def analyze(self, price_data: List[float], pe_data: List[float] = None, pb_data: List[float] = None) -> Dict[str, Any]:
        """综合分析周期"""
        # 价格周期分析
        price_analysis = self.lstm_model.analyze_cycle(price_data)

        result = {
            "price_cycle": price_analysis,
            "timestamp": pd.Timestamp.now().isoformat(),
        }

        # PE周期分析
        if pe_data and len(pe_data) >= 60:
            pe_model = LSTMModel(sequence_length=60)
            pe_analysis = pe_model.analyze_cycle(pe_data)
            result["pe_cycle"] = pe_analysis

        # PB周期分析
        if pb_data and len(pb_data) >= 60:
            pb_model = LSTMModel(sequence_length=60)
            pb_analysis = pb_model.analyze_cycle(pb_data)
            result["pb_cycle"] = pb_analysis

        # 综合建议
        result["overall_recommendation"] = self._generate_recommendation(result)

        return result

    def _generate_recommendation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合建议"""
        recommendations = []
        confidences = []

        if "price_cycle" in analysis:
            rec = analysis["price_cycle"].get("recommendation", "持有观望")
            recommendations.append(rec)
            confidences.append(analysis["price_cycle"].get("prediction", {}).get("confidence", 50))

        if "pe_cycle" in analysis:
            rec = analysis["pe_cycle"].get("recommendation", "持有观望")
            recommendations.append(rec)
            confidences.append(analysis["pe_cycle"].get("prediction", {}).get("confidence", 50))

        # 简单多数投票
        if len(recommendations) > 0:
            from collections import Counter
            most_common = Counter(recommendations).most_common(1)[0][0]
            avg_confidence = sum(confidences) / len(confidences)
        else:
            most_common = "持有观望"
            avg_confidence = 50

        return {
            "action": most_common,
            "confidence": round(avg_confidence, 1),
            "factors_considered": len(recommendations),
        }
