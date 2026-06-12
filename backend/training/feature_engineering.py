"""LSTM 训练特征工程：PE/PB 估值分位等"""
from __future__ import annotations

import numpy as np
import pandas as pd

from training.config import LSTM_FEATURE_NAMES, PERCENTILE_WINDOW

DEFAULT_NEUTRAL_PERCENTILE = 0.5


def rolling_minmax_percentile(series: pd.Series, window: int = PERCENTILE_WINDOW) -> pd.Series:
    """
    估值分位：(当前值 - 过去 N 日最小值) / (过去 N 日最大值 - 过去 N 日最小值)
    """
    s = pd.to_numeric(series, errors="coerce")
    min_periods = max(30, window // 5)
    roll_min = s.rolling(window, min_periods=min_periods).min()
    roll_max = s.rolling(window, min_periods=min_periods).max()
    denom = (roll_max - roll_min).replace(0, np.nan)
    pct = (s - roll_min) / denom
    return pct.fillna(DEFAULT_NEUTRAL_PERCENTILE).clip(0.0, 1.0)


def enrich_stock_features(df: pd.DataFrame) -> pd.DataFrame:
    """为单只股票日线数据增加 pct_chg、PE/PB 分位等 LSTM 输入特征"""
    if df.empty:
        return df

    out = df.sort_values("trade_date").copy()
    for col in ("close", "pct_chg", "vol", "pe", "pb"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "pct_chg" not in out.columns or out["pct_chg"].isna().all():
        out["pct_chg"] = out["close"].pct_change() * 100

    if "vol" not in out.columns:
        out["vol"] = 0.0

    pe_series = out["pe"].ffill().bfill() if "pe" in out.columns else pd.Series(dtype=float)
    pb_series = out["pb"].ffill().bfill() if "pb" in out.columns else pd.Series(dtype=float)

    if pe_series.notna().any():
        out["pe_pct"] = rolling_minmax_percentile(pe_series)
    else:
        out["pe_pct"] = DEFAULT_NEUTRAL_PERCENTILE

    if pb_series.notna().any():
        out["pb_pct"] = rolling_minmax_percentile(pb_series)
    else:
        out["pb_pct"] = DEFAULT_NEUTRAL_PERCENTILE

    out["vol"] = out["vol"].fillna(0)
    out["pct_chg"] = out["pct_chg"].fillna(0)
    return out


def build_feature_matrix(group: pd.DataFrame) -> np.ndarray:
    """返回 shape (T, n_features) 的特征矩阵"""
    enriched = enrich_stock_features(group)
    cols = [c for c in LSTM_FEATURE_NAMES if c in enriched.columns]
    matrix = enriched[cols].astype(float).values
    if matrix.shape[1] != len(LSTM_FEATURE_NAMES):
        raise ValueError(f"特征列不完整: 期望 {LSTM_FEATURE_NAMES}, 实际 {cols}")
    return matrix
