"""
训练数据准备：
1. 沪深300成分股
2. 近 N 年日线 (open/high/low/close/vol/amount)
3. 近 N 年估值 (pe/pb/ps/pct_chg via daily + daily_basic)
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from training.config import DATA_DIR, HS300_INDEX, SKIP_DAILY_BASIC, STOCK_LIMIT, TRAIN_YEARS
from training.tushare_client import fetch_hs300_members, query


def _date_range(years: int) -> tuple[str, str]:
    end = datetime.now()
    start = end - timedelta(days=365 * years)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def fetch_stock_daily(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    df = query("daily", {"ts_code": ts_code, "start_date": start_date, "end_date": end_date})
    if df.empty:
        return df
    df = df.sort_values("trade_date").reset_index(drop=True)
    return df


def fetch_stock_valuation(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        df = query("daily_basic", {"ts_code": ts_code, "start_date": start_date, "end_date": end_date})
        if df.empty:
            return df
        keep = [c for c in ["trade_date", "pe", "pb", "ps", "turnover_rate", "total_mv"] if c in df.columns]
        return df[keep].sort_values("trade_date").reset_index(drop=True)
    except Exception as e:
        print(f"    [估值] {ts_code} 跳过: {e}")
        return pd.DataFrame()


def merge_stock_data(daily: pd.DataFrame, basic: pd.DataFrame) -> pd.DataFrame:
    if daily.empty:
        return daily
    merged = daily.copy()
    if not basic.empty:
        merged = merged.merge(basic, on="trade_date", how="left")
    if "pct_chg" not in merged.columns and "close" in merged.columns:
        merged["pct_chg"] = merged["close"].pct_change() * 100
    merged["ts_code"] = merged.get("ts_code", daily.get("ts_code", ""))
    return merged


def prepare_training_data(
    stock_limit: int = STOCK_LIMIT,
    years: int = TRAIN_YEARS,
    force_refresh: bool = False,
) -> pd.DataFrame:
    cache_path = DATA_DIR / f"hs300_merged_{years}y_{stock_limit or 'all'}.csv"
    parquet_path = cache_path.with_suffix(".parquet")
    if parquet_path.exists() and not force_refresh:
        print(f"[数据] 从缓存加载: {parquet_path}")
        return pd.read_parquet(parquet_path)
    if cache_path.exists() and not force_refresh:
        print(f"[数据] 从缓存加载: {cache_path}")
        return pd.read_csv(cache_path)

    start_date, end_date = _date_range(years)
    members = fetch_hs300_members(HS300_INDEX)
    if stock_limit > 0:
        members = members[:stock_limit]
    print(f"[数据] 沪深300成分股 {len(members)} 只，区间 {start_date} ~ {end_date}")

    frames: list[pd.DataFrame] = []
    for i, code in enumerate(members, 1):
        print(f"  [{i}/{len(members)}] {code} ...", end=" ", flush=True)
        try:
            daily = fetch_stock_daily(code, start_date, end_date)
            basic = pd.DataFrame()
            if not SKIP_DAILY_BASIC:
                basic = fetch_stock_valuation(code, start_date, end_date)
            merged = merge_stock_data(daily, basic)
            if merged.empty or len(merged) < 60:
                print("跳过(数据不足)")
                continue
            merged["ts_code"] = code
            frames.append(merged)
            print(f"OK ({len(merged)} 行)")
        except Exception as e:
            print(f"失败: {e}")

    if not frames:
        raise RuntimeError("未能获取任何股票训练数据，请检查 TUSHARE_TOKEN 与积分权限")

    all_data = pd.concat(frames, ignore_index=True)
    try:
        all_data.to_parquet(parquet_path, index=False)
        print(f"[数据] 已保存 {len(all_data)} 行 -> {parquet_path}")
    except Exception:
        all_data.to_csv(cache_path, index=False)
        print(f"[数据] 已保存 {len(all_data)} 行 -> {cache_path}")
    return all_data


def main() -> None:
    parser = argparse.ArgumentParser(description="准备灵析训练数据")
    parser.add_argument("--limit", type=int, default=STOCK_LIMIT, help="股票数量上限，0=不限制")
    parser.add_argument("--years", type=int, default=TRAIN_YEARS, help="历史年数")
    parser.add_argument("--refresh", action="store_true", help="强制重新拉取")
    args = parser.parse_args()

    limit = args.limit if args.limit > 0 else 300
    prepare_training_data(stock_limit=limit, years=args.years, force_refresh=args.refresh)


if __name__ == "__main__":
    main()
