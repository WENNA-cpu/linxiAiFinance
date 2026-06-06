# LSTM 周期预测模型评估报告

生成时间: 2026-06-05 19:29:42

## 模型信息
- 模型路径: `E:\linxiAiFinance\backend\models\lstm_cycle.h5`
- 输入窗口: 30 天
- 预测步长: 5 天
- 测试样本: 1804

## 评估指标
| 指标 | 值 |
|------|-----|
| RMSE | 13.7463 |
| MAE  | 4.8561 |

## 说明
- RMSE/MAE 基于反归一化后的收盘价（元）计算
- 测试集为随机 20%  hold-out，random_state=42
