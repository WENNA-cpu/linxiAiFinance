"""一键训练流水线：数据准备 -> LSTM -> RF -> 评估"""
import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from training.config import STOCK_LIMIT, TRAIN_YEARS
from training.data_fetch import prepare_training_data
from training.train_lstm import train_lstm
from training.train_rf import train_rf
from training.evaluate_lstm import evaluate_lstm
from training.evaluate_rf import evaluate_rf


def main() -> None:
    parser = argparse.ArgumentParser(description="灵析模型一键训练")
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT)
    parser.add_argument("--years", type=int, default=TRAIN_YEARS)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    limit = args.limit if args.limit > 0 else 300
    print("=" * 50)
    print("1/5 准备训练数据")
    prepare_training_data(stock_limit=limit, years=args.years, force_refresh=args.refresh)

    print("=" * 50)
    print("2/5 训练 LSTM")
    train_lstm(stock_limit=limit, years=args.years, epochs=args.epochs)

    print("=" * 50)
    print("3/5 评估 LSTM")
    evaluate_lstm(stock_limit=limit, years=args.years)

    print("=" * 50)
    print("4/5 训练随机森林")
    train_rf(stock_limit=limit, years=args.years)

    print("=" * 50)
    print("5/5 评估随机森林")
    evaluate_rf(stock_limit=limit, years=args.years)

    print("=" * 50)
    print("全部完成！")


if __name__ == "__main__":
    main()
