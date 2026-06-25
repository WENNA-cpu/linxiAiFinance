# 随机森林 v2.1 风险评级模型评估报告

生成时间: 2026-06-23 11:01:35

## 模型信息
- 模型路径: `E:\linxiAiFinance\backend\models\rf_risk_v2.1.pkl`
- 特征 (11): volatility, turnover_rate, pe_percentile, pb_percentile, volume_change_rate, amplitude, rsi_14, ma5_bias, ma20_bias, bollinger_width, vol_ma5_ratio
- 训练区间: 近 3 年
- 测试样本: 2736

## 整体指标
| 指标 | 值 |
|------|-----|
| 准确率 | 0.5691 |
| 召回率 (macro) | 0.5696 |
| F1 (macro) | 0.5673 |

## 新增技术指标
- RSI(14)、MA5/MA20 乖离率、布林带宽度、成交量 MA5 比值

## 各类别指标
| 类别 | Precision | Recall | F1 |
|------|-----------|--------|-----|
| 低风险 | 0.5560 | 0.6925 | 0.6167 |
| 中风险 | 0.5250 | 0.5086 | 0.5167 |
| 高风险 | 0.6456 | 0.5077 | 0.5684 |