# 随机森林 v2.0 风险评级模型评估报告

生成时间: 2026-06-23 09:34:45

## 模型信息
- 模型路径: `E:\linxiAiFinance\backend\models\rf_risk_v2.0.pkl`
- 特征: volatility, turnover_rate, pe_percentile, pb_percentile, volume_change_rate, amplitude
- 训练区间: 近 3 年
- 测试样本: 2736

## 整体指标
| 指标 | 值 |
|------|-----|
| 准确率 | 0.5482 |
| 召回率 (macro) | 0.5490 |
| F1 (macro) | 0.5474 |

## 各类别指标
| 类别 | Precision | Recall | F1 |
|------|-----------|--------|-----|
| 低风险 | 0.5350 | 0.6427 | 0.5839 |
| 中风险 | 0.4971 | 0.4580 | 0.4767 |
| 高风险 | 0.6214 | 0.5465 | 0.5815 |