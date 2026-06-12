"""对比 LSTM 基线（仅收盘价）与增强模型（含 PE/PB 分位）的 RMSE / MAE"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from training.config import (
    LSTM_BASELINE_MODEL_PATH,
    LSTM_BASELINE_SCALER_PATH,
    LSTM_COMPARE_REPORT,
    LSTM_MODEL_PATH,
    LSTM_SCALER_PATH,
    STOCK_LIMIT,
    TRAIN_YEARS,
)
from training.evaluate_lstm import evaluate_lstm


def compare_lstm(stock_limit: int = STOCK_LIMIT, years: int = TRAIN_YEARS) -> dict:
    if not LSTM_BASELINE_MODEL_PATH.exists() and LSTM_MODEL_PATH.exists():
        shutil.copy2(LSTM_MODEL_PATH, LSTM_BASELINE_MODEL_PATH)
        shutil.copy2(LSTM_SCALER_PATH, LSTM_BASELINE_SCALER_PATH)

    if not LSTM_BASELINE_MODEL_PATH.exists():
        raise FileNotFoundError("未找到基线模型，请先保留旧版 lstm_cycle.h5 或运行一次训练前备份")

    baseline = evaluate_lstm(
        stock_limit=stock_limit,
        years=years,
        model_path=LSTM_BASELINE_MODEL_PATH,
        scaler_path=LSTM_BASELINE_SCALER_PATH,
    )
    enhanced = evaluate_lstm(
        stock_limit=stock_limit,
        years=years,
        model_path=LSTM_MODEL_PATH,
        scaler_path=LSTM_SCALER_PATH,
    )

    rmse_delta = baseline["rmse"] - enhanced["rmse"]
    mae_delta = baseline["mae"] - enhanced["mae"]
    rmse_pct = (rmse_delta / baseline["rmse"] * 100) if baseline["rmse"] else 0
    mae_pct = (mae_delta / baseline["mae"] * 100) if baseline["mae"] else 0

    improved = rmse_delta > 0 and mae_delta > 0
    verdict = "增强模型更优" if improved else "增强模型未全面优于基线（可能需更多数据/训练轮次）"

    report = f"""# LSTM 模型对比报告（基线 vs PE/PB 分位增强）

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 数据与特征
| 项目 | 基线模型 | 增强模型 |
|------|----------|----------|
| 输入特征 | 收盘价 | 收盘价、涨跌幅、成交量、PE 分位、PB 分位 |
| 估值分位窗口 | — | 252 交易日 |
| 训练数据年数 | {years} | {years} |
| 股票数量上限 | {stock_limit} | {stock_limit} |

## 评估指标对比
| 指标 | 基线 | 增强 | 变化 | 相对提升 |
|------|------|------|------|----------|
| RMSE | {baseline["rmse"]:.4f} | {enhanced["rmse"]:.4f} | {rmse_delta:+.4f} | {rmse_pct:+.2f}% |
| MAE  | {baseline["mae"]:.4f} | {enhanced["mae"]:.4f} | {mae_delta:+.4f} | {mae_pct:+.2f}% |

## 结论
- **{verdict}**
- RMSE {'降低' if rmse_delta > 0 else '升高'} {abs(rmse_pct):.2f}%
- MAE {'降低' if mae_delta > 0 else '升高'} {abs(mae_pct):.2f}%

## 说明
- 正值「变化」表示增强模型误差更低（更好）
- 测试集划分 random_state=42，与 evaluate_lstm.py 一致
- 若 PE/PB 来自 Tushare daily_basic，需足够积分与拉取时间
"""
    LSTM_COMPARE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    LSTM_COMPARE_REPORT.write_text(report, encoding="utf-8")
    print(f"[对比] 报告: {LSTM_COMPARE_REPORT}")
    print(f"[对比] 基线 RMSE={baseline['rmse']:.4f}, 增强 RMSE={enhanced['rmse']:.4f}")

    return {
        "baseline": baseline,
        "enhanced": enhanced,
        "rmse_improvement_pct": round(rmse_pct, 2),
        "mae_improvement_pct": round(mae_pct, 2),
        "report": str(LSTM_COMPARE_REPORT),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS)
    args = parser.parse_args()
    limit = args.limit if args.limit > 0 else 300
    compare_lstm(stock_limit=limit, years=args.years)


if __name__ == "__main__":
    main()
