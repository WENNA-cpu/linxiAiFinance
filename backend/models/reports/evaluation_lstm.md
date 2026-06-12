# LSTM 周期预测模型评估报告

生成时间: 2026-06-12 08:40:09

## 模型信息
- 模型路径: `E:\linxiAiFinance\backend\models\lstm_cycle.h5`
- 输入窗口: 30 天
- 预测步长: 5 天
- 输入特征: ['close', 'pct_chg', 'vol', 'pe_pct', 'pb_pct']
- 测试样本: 4701

## 评估指标
| 指标 | 值 |
|------|-----|
| RMSE | 14.5628 |
| MAE  | 5.4794 |

## 说明
- RMSE/MAE 基于反归一化后的收盘价（元）计算
- 测试集为随机 20% hold-out，random_state=42
