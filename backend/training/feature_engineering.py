"""LSTM 训练特征工程：PE/PB 估值分位等"""
from __future__ import annotations

import numpy as np
import pandas as pd

from training.config import LSTM_FEATURE_NAMES, PERCENTILE_WINDOW

DEFAULT_NEUTRAL_PERCENTILE = 0.5


def add_pe_pb_percentile(df: pd.DataFrame) -> pd.DataFrame:
    """
    为 DataFrame 添加 PE 分位和 PB 分位列
    """
    if "pe" in df.columns and df["pe"].notna().sum() > 0:
        df["pe_percentile"] = df["pe"].rank(pct=True)
    else:
        df["pe_percentile"] = DEFAULT_NEUTRAL_PERCENTILE

    if "pb" in df.columns and df["pb"].notna().sum() > 0:
        df["pb_percentile"] = df["pb"].rank(pct=True)
    else:
        df["pb_percentile"] = DEFAULT_NEUTRAL_PERCENTILE

    return df


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


def enrich_stock_features_v2(df: pd.DataFrame) -> pd.DataFrame:
    """v2 特征：在 v1 基础上增加 PE/PB 历史分位、换手率、成交量变化率、振幅"""
    if df.empty:
        return df

    out = enrich_stock_features(df)
    out = add_pe_pb_percentile(out)

    for col in ("high", "low", "pre_close", "turnover_rate"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    pre_close = out["pre_close"] if "pre_close" in out.columns else out["close"].shift(1)
    if "high" in out.columns and "low" in out.columns:
        out["amplitude"] = (
            (out["high"] - out["low"]) / pre_close.replace(0, np.nan) * 100
        ).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    else:
        out["amplitude"] = out["pct_chg"].abs().fillna(0.0)

    out["volume_change_rate"] = (
        out["vol"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    )

    if "turnover_rate" not in out.columns or out["turnover_rate"].isna().all():
        vol_ma = out["vol"].rolling(20, min_periods=1).mean()
        out["turnover_rate"] = (out["vol"] / vol_ma.replace(0, np.nan)).fillna(1.0)
    else:
        median_tr = out["turnover_rate"].median()
        out["turnover_rate"] = out["turnover_rate"].fillna(median_tr if pd.notna(median_tr) else 1.0)

    out["pe_percentile"] = out["pe_percentile"].fillna(DEFAULT_NEUTRAL_PERCENTILE)
    out["pb_percentile"] = out["pb_percentile"].fillna(DEFAULT_NEUTRAL_PERCENTILE)
    return out


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI 相对强弱指标"""
    s = pd.to_numeric(close, errors="coerce")
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0).clip(0.0, 100.0)


def compute_ma_bias(close: pd.Series, window: int) -> pd.Series:
    """均线乖离率：(收盘价 - N日均线) / N日均线"""
    s = pd.to_numeric(close, errors="coerce")
    ma = s.rolling(window, min_periods=window).mean()
    bias = (s - ma) / ma.replace(0, np.nan)
    return bias.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def compute_bollinger_width(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """布林带宽度：(上轨 - 下轨) / 中轨"""
    s = pd.to_numeric(close, errors="coerce")
    mid = s.rolling(window, min_periods=window).mean()
    std = s.rolling(window, min_periods=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid.replace(0, np.nan)
    return width.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def compute_vol_ma5_ratio(vol: pd.Series) -> pd.Series:
    """成交量 MA5 比值：当前成交量 / 5日均量"""
    s = pd.to_numeric(vol, errors="coerce").fillna(0.0)
    ma5 = s.rolling(5, min_periods=5).mean()
    ratio = s / ma5.replace(0, np.nan)
    return ratio.replace([np.inf, -np.inf], np.nan).fillna(1.0)


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """从现有 OHLCV 数据计算 RSI、均线乖离、布林带宽度、量比等技术指标"""
    if df.empty:
        return df

    out = df.sort_values("trade_date").copy()
    close = pd.to_numeric(out.get("close"), errors="coerce")
    vol = pd.to_numeric(out.get("vol"), errors="coerce").fillna(0.0)

    out["rsi_14"] = compute_rsi(close, period=14)
    out["ma5_bias"] = compute_ma_bias(close, window=5)
    out["ma20_bias"] = compute_ma_bias(close, window=20)
    out["bollinger_width"] = compute_bollinger_width(close, window=20)
    out["vol_ma5_ratio"] = compute_vol_ma5_ratio(vol)
    return out


def build_feature_matrix_v2(group: pd.DataFrame, feature_names: list[str] | None = None) -> np.ndarray:
    """v2 LSTM 特征矩阵"""
    from training.config import LSTM_V2_FEATURE_NAMES

    names = feature_names or LSTM_V2_FEATURE_NAMES
    enriched = enrich_stock_features_v2(group)
    cols = [c for c in names if c in enriched.columns]
    matrix = enriched[cols].astype(float).values
    if matrix.shape[1] != len(names):
        raise ValueError(f"特征列不完整: 期望 {names}, 实际 {cols}")
    return matrix


def build_feature_matrix(group: pd.DataFrame) -> np.ndarray:
    """返回 shape (T, n_features) 的特征矩阵"""
    enriched = enrich_stock_features(group)
    cols = [c for c in LSTM_FEATURE_NAMES if c in enriched.columns]
    matrix = enriched[cols].astype(float).values
    if matrix.shape[1] != len(LSTM_FEATURE_NAMES):
        raise ValueError(f"特征列不完整: 期望 {LSTM_FEATURE_NAMES}, 实际 {cols}")
    return matrix
