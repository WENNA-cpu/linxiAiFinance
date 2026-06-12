"""同步 Tushare HTTP 客户端（训练脚本专用）"""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from training.config import TUSHARE_TOKEN

BASE_URL = "https://api.tushare.pro"
_MIN_INTERVAL = 0.35
_BASIC_INTERVAL = 61.0
_HOURLY_BASIC_INTERVAL = 3605.0
_last_call = 0.0
_daily_basic_hourly_blocked = False

BACKEND = Path(__file__).resolve().parents[1]
CACHE_DIR = BACKEND / "data" / "cache" / "tushare"


def _throttle(api_name: str) -> None:
    global _last_call
    interval = _BASIC_INTERVAL if api_name == "daily_basic" else _MIN_INTERVAL
    elapsed = time.time() - _last_call
    if elapsed < interval:
        time.sleep(interval - elapsed)
    _last_call = time.time()


def load_daily_basic_cache(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """从 data_service 磁盘缓存加载 daily_basic（训练用，忽略 TTL）"""
    safe = ts_code.replace(".", "_")
    path = CACHE_DIR / f"daily_basic_{safe}.json"
    if not path.exists():
        return pd.DataFrame()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("rows") or []
        filtered = [
            r for r in rows
            if start_date <= str(r.get("trade_date", "")) <= end_date
        ]
        if not filtered:
            return pd.DataFrame()
        df = pd.DataFrame(filtered)
        keep = [c for c in ["trade_date", "pe", "pb", "ps", "turnover_rate", "total_mv"] if c in df.columns]
        return df[keep].sort_values("trade_date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def save_daily_basic_cache(ts_code: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        safe = ts_code.replace(".", "_")
        path = CACHE_DIR / f"daily_basic_{safe}.json"
        rows = df.to_dict(orient="records")
        path.write_text(json.dumps({"ts": time.time(), "rows": rows}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def query(api_name: str, params: Optional[Dict[str, Any]] = None, retries: int = 2) -> pd.DataFrame:
    """调用 Tushare API 并返回 DataFrame"""
    global _daily_basic_hourly_blocked
    if api_name == "daily_basic" and _daily_basic_hourly_blocked:
        raise RuntimeError("daily_basic 本小时已限流，请使用本地缓存")

    if not TUSHARE_TOKEN:
        raise RuntimeError("未配置 TUSHARE_TOKEN")

    last_err = ""
    for attempt in range(retries + 1):
        _throttle(api_name)
        payload = {"api_name": api_name, "token": TUSHARE_TOKEN, "params": params or {}}
        try:
            resp = requests.post(BASE_URL, json=payload, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                msg = result.get("msg", str(result))
                if "1次/小时" in msg or "1次/小時" in msg:
                    _daily_basic_hourly_blocked = True
                    raise RuntimeError(f"Tushare {api_name} 失败: {msg}")
                if ("频率" in msg or "每分钟" in msg) and attempt < retries:
                    time.sleep(_BASIC_INTERVAL)
                    last_err = msg
                    continue
                raise RuntimeError(f"Tushare {api_name} 失败: {msg}")
            data = result.get("data") or {}
            fields = data.get("fields") or []
            items = data.get("items") or []
            return pd.DataFrame(items, columns=fields) if items else pd.DataFrame(columns=fields)
        except RuntimeError:
            raise
        except Exception as e:
            last_err = str(e)
            if attempt < retries:
                time.sleep(_BASIC_INTERVAL)
    raise RuntimeError(last_err or f"Tushare {api_name} 失败")


def fetch_hs300_members(index_code: str = "399300.SZ") -> List[str]:
    """获取沪深300成分股列表"""
    fallback = [
        "600519.SH", "000001.SZ", "600036.SH", "601318.SH", "000858.SZ",
        "600276.SH", "601166.SH", "600900.SH", "000333.SZ", "002415.SZ",
        "601398.SH", "600030.SH", "601888.SH", "000651.SZ", "601012.SH",
        "600887.SH", "002594.SZ", "300750.SZ", "601857.SH", "600050.SH",
        "601288.SH", "600028.SH", "601988.SH", "000725.SZ", "002304.SZ",
    ]
    try:
        end = pd.Timestamp.now().strftime("%Y%m%d")
        start = (pd.Timestamp.now() - pd.DateOffset(months=3)).strftime("%Y%m%d")
        df = query("index_weight", {"index_code": index_code, "start_date": start, "end_date": end}, retries=0)
        if not df.empty and "con_code" in df.columns:
            codes = df["con_code"].dropna().unique().tolist()
            if codes:
                return sorted(codes)
        df = query("index_member", {"index_code": index_code}, retries=0)
        if not df.empty and "con_code" in df.columns:
            return sorted(df["con_code"].dropna().unique().tolist())
    except Exception as e:
        print(f"[数据] 成分股接口受限，使用内置列表: {e}")
    return fallback
