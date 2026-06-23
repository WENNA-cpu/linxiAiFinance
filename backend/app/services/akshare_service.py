"""AKShare 数据服务 — Tushare daily_basic 的补充/降级数据源"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _normalize_ts_code(ts_code: str) -> str:
    if "." in ts_code:
        return ts_code.upper()
    code = ts_code.strip()
    if code.startswith(("6", "5", "9")):
        return f"{code}.SH"
    return f"{code}.SZ"


def _bare_symbol(ts_code: str) -> str:
    return _normalize_ts_code(ts_code).split(".")[0]


def _date_to_yyyymmdd(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, str):
        return value.replace("-", "").strip()[:8]
    return pd.Timestamp(value).strftime("%Y%m%d")


def _safe_float(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        v = float(value)
        if pd.isna(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def _fetch_lg_indicator(symbol: str) -> pd.DataFrame:
    """
    获取 PE/PB 估值指标。
    优先 stock_a_lg_indicator（旧版 AKShare），不可用则降级 stock_value_em。
    """
    import akshare as ak

    if hasattr(ak, "stock_a_lg_indicator"):
        try:
            raw = ak.stock_a_lg_indicator(stock=symbol)
            if raw is not None and not raw.empty:
                df = raw.reset_index()
                if "trade_date" not in df.columns:
                    df.rename(columns={df.columns[0]: "trade_date"}, inplace=True)
                df["trade_date"] = df["trade_date"].apply(_date_to_yyyymmdd)
                for col in ("pe", "pe_ttm", "pb", "ps_ttm", "total_mv"):
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                return df
        except Exception as exc:
            logger.warning("stock_a_lg_indicator 失败 %s: %s", symbol, exc)

    try:
        df = ak.stock_value_em(symbol=symbol)
    except Exception as exc:
        logger.warning("stock_value_em 失败 %s: %s", symbol, exc)
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    out = pd.DataFrame()
    out["trade_date"] = df["数据日期"].apply(_date_to_yyyymmdd)
    out["close"] = pd.to_numeric(df.get("当日收盘价"), errors="coerce")
    out["pe"] = pd.to_numeric(df.get("PE(静)"), errors="coerce")
    out["pe_ttm"] = pd.to_numeric(df.get("PE(TTM)"), errors="coerce")
    out["pb"] = pd.to_numeric(df.get("市净率"), errors="coerce")
    out["ps"] = pd.to_numeric(df.get("市销率"), errors="coerce")
    out["ps_ttm"] = pd.to_numeric(df.get("市销率"), errors="coerce")
    # Tushare total_mv 单位为万元；东财为元
    out["total_mv"] = pd.to_numeric(df.get("总市值"), errors="coerce") / 10000.0
    out["circ_mv"] = pd.to_numeric(df.get("流通市值"), errors="coerce") / 10000.0
    out["total_share"] = pd.to_numeric(df.get("总股本"), errors="coerce") / 10000.0
    out["float_share"] = pd.to_numeric(df.get("流通股本"), errors="coerce") / 10000.0
    return out


def _fetch_turnover(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """从 stock_zh_a_hist 获取换手率（失败时返回空表，不阻断估值数据）"""
    import time

    import akshare as ak

    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            hist = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="",
            )
            if hist is None or hist.empty:
                return pd.DataFrame()

            out = pd.DataFrame()
            out["trade_date"] = hist["日期"].apply(_date_to_yyyymmdd)
            out["turnover_rate"] = pd.to_numeric(hist.get("换手率"), errors="coerce")
            if "收盘" in hist.columns:
                out["hist_close"] = pd.to_numeric(hist["收盘"], errors="coerce")
            return out
        except Exception as exc:
            last_exc = exc
            if attempt == 0:
                time.sleep(1.5)

    logger.warning("stock_zh_a_hist 失败 %s: %s", symbol, last_exc)
    return pd.DataFrame()


def _normalize_lg_row(ts_code: str, row: pd.Series) -> Dict[str, Any]:
    """将指标行转为 Tushare daily_basic 兼容结构"""
    trade_date = _date_to_yyyymmdd(row.get("trade_date"))
    pe = _safe_float(row.get("pe"))
    pe_ttm = _safe_float(row.get("pe_ttm"))
    pb = _safe_float(row.get("pb"))
    ps = _safe_float(row.get("ps") or row.get("ps_ttm"))
    ps_ttm = _safe_float(row.get("ps_ttm") or row.get("ps"))
    total_mv = _safe_float(row.get("total_mv"))
    if total_mv is not None and total_mv > 1e8:
        total_mv = total_mv / 10000.0
    circ_mv = _safe_float(row.get("circ_mv"))
    if circ_mv is not None and circ_mv > 1e8:
        circ_mv = circ_mv / 10000.0

    return {
        "ts_code": ts_code,
        "trade_date": trade_date,
        "close": _safe_float(row.get("close")),
        "turnover_rate": _safe_float(row.get("turnover_rate")),
        "pe": pe if pe is not None else pe_ttm,
        "pe_ttm": pe_ttm if pe_ttm is not None else pe,
        "pb": pb,
        "ps": ps,
        "ps_ttm": ps_ttm,
        "total_mv": total_mv,
        "circ_mv": circ_mv,
        "total_share": _safe_float(row.get("total_share")),
        "float_share": _safe_float(row.get("float_share")),
        "data_source": "akshare",
    }


def get_daily_basic(ts_code: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    获取 daily_basic 兼容数据（PE/PB/换手率等）。
    合并 stock_a_lg_indicator（或 stock_value_em）与 stock_zh_a_hist。
    """
    ts_code = _normalize_ts_code(ts_code)
    symbol = _bare_symbol(ts_code)
    start_date = str(start_date).replace("-", "")[:8]
    end_date = str(end_date).replace("-", "")[:8]

    indicator = _fetch_lg_indicator(symbol)
    if indicator.empty:
        logger.warning("[AKShare] %s 无估值指标数据", ts_code)
        return []

    turnover = _fetch_turnover(symbol, start_date, end_date)
    if not turnover.empty:
        indicator = indicator.merge(turnover, on="trade_date", how="left", suffixes=("", "_hist"))
        if "hist_close" in indicator.columns and indicator["close"].isna().all():
            indicator["close"] = indicator["hist_close"]

    indicator = indicator[
        (indicator["trade_date"] >= start_date) & (indicator["trade_date"] <= end_date)
    ]
    indicator = indicator.sort_values("trade_date", ascending=False)

    rows: List[Dict[str, Any]] = []
    for _, row in indicator.iterrows():
        item = _normalize_lg_row(ts_code, row)
        if item.get("trade_date"):
            rows.append(item)

    logger.info("[AKShare] %s daily_basic %s~%s -> %d 条", ts_code, start_date, end_date, len(rows))
    return rows
