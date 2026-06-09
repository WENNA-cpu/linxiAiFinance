# LSTM 周期预测模型评估报告

生成时间: 2026-06-08 09:07:44

## 模型信息
- 模型路径: `E:\linxiAiFinance\backend\models\lstm_cycle.h5`
- 输入窗口: 30 天
- 预测步长: 5 天
- 测试样本: 1624

## 评估指标
| 指标 | 值 |
|------|-----|
| RMSE | 356.9721 |
| MAE  | 129.1978 |

## 说明
- RMSE/MAE 基于反归一化后的收盘价（元）计算
- 测试集为随机 20%  hold-out，random_state=42
