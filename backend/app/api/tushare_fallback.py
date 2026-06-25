"""Tushare 调用失败时的统一告警与 Mock 工具"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.data_service import DataService


def warn_tushare_mock(detail: str = "") -> None:
    msg = "Tushare 限流或错误，使用 Mock 数据"
    if detail:
        print(f"{msg} — {detail}")
    else:
        print(msg)


# 常见资产 Mock 行情（与 daily 字段一致）
_MOCK_QUOTE_ROWS: Dict[str, Dict[str, Any]] = {
    "000001.SZ": {
        "ts_code": "000001.SZ",
        "trade_date": "20260612",
        "open": 11.0,
        "high": 11.25,
        "low": 10.88,
        "close": 11.24,
        "pre_close": 10.94,
        "change": 0.3,
        "pct_chg": 2.74,
        "vol": 2032355.46,
        "amount": 2263042.93,
        "data_source": "mock",
    },
    "600519.SH": {
        "ts_code": "600519.SH",
        "trade_date": "20260612",
        "open": 1271.18,
        "high": 1295.0,
        "low": 1265.01,
        "close": 1291.91,
        "pre_close": 1279.0,
        "change": 12.91,
        "pct_chg": 1.01,
        "vol": 50494.78,
        "amount": 6477910.21,
        "data_source": "mock",
    },
    "510050.SH": {
        "ts_code": "510050.SH",
        "trade_date": "20260611",
        "open": 2.91,
        "high": 2.935,
        "low": 2.905,
        "close": 2.923,
        "pre_close": 2.905,
        "change": 0.018,
        "pct_chg": 0.62,
        "vol": 1250000,
        "amount": 3640000,
        "data_source": "mock",
    },
}


def mock_quote_row(code: str, asset_type: Optional[str] = None) -> Dict[str, Any]:
    """返回与 Tushare daily 一致结构的 Mock 行情"""
    ts_code = DataService._normalize_ts_code(code)
    svc = DataService()
    fund_mock = svc._mock_quote(ts_code)
    if fund_mock:
        row = dict(fund_mock)
        row["data_source"] = "mock"
        return row

    bare = ts_code.split(".")[0]
    row = _MOCK_QUOTE_ROWS.get(ts_code) or _MOCK_QUOTE_ROWS.get(bare)
    if row:
        return dict(row)

    return {
        "ts_code": ts_code,
        "trade_date": datetime.now().strftime("%Y%m%d"),
        "open": 10.0,
        "high": 10.0,
        "low": 10.0,
        "close": 10.0,
        "pre_close": 10.0,
        "change": 0.0,
        "pct_chg": 0.0,
        "vol": 0.0,
        "amount": 0.0,
        "data_source": "mock",
    }


def mock_market_data(ts_code: str) -> Dict[str, Any]:
    quote = mock_quote_row(ts_code)
    return {
        "ts_code": DataService._normalize_ts_code(ts_code),
        "trade_date": quote.get("trade_date", ""),
        "open": quote.get("open", 0),
        "high": quote.get("high", 0),
        "low": quote.get("low", 0),
        "close": quote.get("close", 0),
        "pre_close": quote.get("pre_close", 0),
        "change": quote.get("change", 0),
        "pct_chg": quote.get("pct_chg", 0),
        "vol": quote.get("vol", 0),
        "amount": quote.get("amount", 0),
        "valuation": mock_valuation(ts_code),
        "history": [quote],
        "data_source": "mock",
    }


def mock_valuation(ts_code: str) -> Dict[str, Any]:
    ts_code = DataService._normalize_ts_code(ts_code)
    return {
        "ts_code": ts_code,
        "trade_date": datetime.now().strftime("%Y%m%d"),
        "pe": 15.0,
        "pb": 2.0,
        "ps": 3.0,
        "turnover_rate": 1.5,
        "data_source": "mock",
    }


def mock_daily_list(ts_code: str) -> List[Dict[str, Any]]:
    return [mock_quote_row(ts_code)]


def mock_index_daily(ts_code: str) -> List[Dict[str, Any]]:
    row = mock_quote_row(ts_code)
    row["ts_code"] = DataService._normalize_ts_code(ts_code)
    return [row]
