# 随机森林风险评级模型评估报告

生成时间: 2026-06-05 19:28:59

## 模型信息
- 模型路径: `E:\linxiAiFinance\backend\models\rf_risk.pkl`
- 特征: volatility, turnover_rate, pe_percentile, volume_change_rate
- 测试样本: 1780

## 整体指标
| 指标 | 值 |
|------|-----|
| 准确率 | 0.4309 |
| F1 (macro) | 0.4281 |
| F1 (weighted) | 0.4276 |

## 各类别指标
| 类别 | Precision | Recall | F1 |
|------|-----------|--------|-----|
| 低风险 | 0.4459 | 0.4558 | 0.4508 |
| 中风险 | 0.4070 | 0.3295 | 0.3641 |
| 高风险 | 0.4348 | 0.5102 | 0.4695 |