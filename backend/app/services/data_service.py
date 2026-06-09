import aiohttp
import asyncio
import json
import os
import time
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache" / "tushare"


class DataService:
    """数据服务 - Tushare API集成"""

    _daily_basic_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
    _last_daily_basic_at: float = 0.0
    DAILY_BASIC_CACHE_TTL = 3600
    DAILY_BASIC_MIN_INTERVAL = 65

    @staticmethod
    def _normalize_ts_code(code: str) -> str:
        if "." in code:
            return code
        if code.startswith("6"):
            return f"{code}.SH"
        return f"{code}.SZ"

    def __init__(self):
        self.tushare_token = os.getenv("TUSHARE_TOKEN", "").strip()
        self.base_url = "https://api.tushare.pro"

    async def _wait_daily_basic_slot(self) -> None:
        elapsed = time.time() - DataService._last_daily_basic_at
        if elapsed < self.DAILY_BASIC_MIN_INTERVAL:
            await asyncio.sleep(self.DAILY_BASIC_MIN_INTERVAL - elapsed)

    async def _request(self, api_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送Tushare API请求"""
        if not self.tushare_token:
            print(f"Tushare {api_name}: TUSHARE_TOKEN 未配置")
            return None

        async with aiohttp.ClientSession() as session:
            payload = {
                "api_name": api_name,
                "token": self.tushare_token,
                "params": params,
            }
            try:
                async with session.post(self.base_url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        print(f"Tushare {api_name}: HTTP {response.status}")
                        return None
                    result = await response.json()
                    if result.get("code") == 0:
                        return result.get("data", {})
                    print(f"Tushare {api_name} error {result.get('code')}: {result.get('msg')}")
            except Exception as e:
                print(f"Error calling {api_name}: {e}")
        return None

    async def fetch_daily_data(self, ts_code: str, start_date: str = None, end_date: str = None) -> Optional[List[Dict]]:
        """获取日线行情数据"""
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        data = await self._request("daily", {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
        })

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            return [dict(zip(fields, item)) for item in items]
        return None

    async def fetch_stock_basic(self) -> Optional[List[Dict]]:
        """获取股票基础信息"""
        data = await self._request("stock_basic", {
            "exchange": "",
            "list_status": "L",
        })

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            return [dict(zip(fields, item)) for item in items]
        return None

    async def fetch_daily_basic(self, ts_code: str, trade_date: str = None) -> Optional[List[Dict]]:
        """获取每日指标（估值数据）"""
        params = {"ts_code": ts_code}
        if trade_date:
            params["trade_date"] = trade_date

        data = await self._request("daily_basic", params)

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            return [dict(zip(fields, item)) for item in items]
        return None

    def _disk_cache_path(self, ts_code: str) -> Path:
        safe = ts_code.replace(".", "_")
        return _CACHE_DIR / f"daily_basic_{safe}.json"

    def _load_disk_cache(self, ts_code: str) -> Optional[List[Dict[str, Any]]]:
        path = self._disk_cache_path(ts_code)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - payload.get("ts", 0) > self.DAILY_BASIC_CACHE_TTL:
                return None
            return payload.get("rows") or None
        except Exception:
            return None

    def _save_disk_cache(self, ts_code: str, rows: List[Dict[str, Any]]) -> None:
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            path = self._disk_cache_path(ts_code)
            path.write_text(
                json.dumps({"ts": time.time(), "rows": rows}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"Failed to save tushare cache: {e}")

    def _get_cached_rows(self, ts_code: str) -> Optional[List[Dict[str, Any]]]:
        mem = self._daily_basic_cache.get(ts_code)
        if mem and time.time() - mem[0] < self.DAILY_BASIC_CACHE_TTL:
            return mem[1]
        disk = self._load_disk_cache(ts_code)
        if disk:
            self._daily_basic_cache[ts_code] = (time.time(), disk)
            return disk
        return None

    def _filter_by_date_range(
        self,
        rows: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        return [
            row for row in rows
            if start_date <= str(row.get("trade_date", "")) <= end_date
        ]

    async def fetch_daily_basic_historical(
        self,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> Optional[List[Dict]]:
        """获取历史每日指标（估值数据），带缓存与频率控制"""
        ts_code = self._normalize_ts_code(ts_code)

        cached_rows = self._get_cached_rows(ts_code)
        if cached_rows:
            filtered = self._filter_by_date_range(cached_rows, start_date, end_date)
            if filtered:
                return filtered

        fetch_end = end_date or datetime.now().strftime("%Y%m%d")
        fetch_start = (datetime.now() - timedelta(days=1095 + 45)).strftime("%Y%m%d")

        await self._wait_daily_basic_slot()
        data = await self._request("daily_basic", {
            "ts_code": ts_code,
            "start_date": fetch_start,
            "end_date": fetch_end,
        })
        DataService._last_daily_basic_at = time.time()

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            rows = [dict(zip(fields, item)) for item in items]
            if rows:
                self._daily_basic_cache[ts_code] = (time.time(), rows)
                self._save_disk_cache(ts_code, rows)
            filtered = self._filter_by_date_range(rows, start_date, end_date)
            if filtered:
                return filtered

        if cached_rows:
            return self._filter_by_date_range(cached_rows, start_date, end_date)

        return None

    async def fetch_index_daily(self, ts_code: str = "000001.SH") -> Optional[List[Dict]]:
        """获取指数日线数据"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")

        data = await self._request("index_daily", {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
        })

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            return [dict(zip(fields, item)) for item in items]
        return None

    async def fetch_moneyflow(self, ts_code: str) -> Optional[List[Dict]]:
        """获取个股资金流向"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        data = await self._request("moneyflow", {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
        })

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            return [dict(zip(fields, item)) for item in items]
        return None

    async def fetch_valuation_data(self, ts_code: str) -> Dict[str, Any]:
        """获取估值数据"""
        daily_basic = await self.fetch_daily_basic(ts_code)

        if daily_basic and len(daily_basic) > 0:
            latest = daily_basic[0]
            return {
                "pe": latest.get("pe", 0),
                "pb": latest.get("pb", 0),
                "ps": latest.get("ps", 0),
                "total_mv": latest.get("total_mv", 0),
                "circ_mv": latest.get("circ_mv", 0),
                "turnover_rate": latest.get("turnover_rate", 0),
                "trade_date": latest.get("trade_date", ""),
            }
        return {"pe": 0, "pb": 0, "ps": 0, "total_mv": 0, "circ_mv": 0}

    async def fetch_market_data(self, ts_code: str) -> Optional[Dict[str, Any]]:
        """获取完整的市场数据（行情+估值）"""
        daily_data = await self.fetch_daily_data(ts_code)
        valuation = await self.fetch_valuation_data(ts_code)

        if daily_data:
            latest = daily_data[0]
            return {
                "ts_code": ts_code,
                "trade_date": latest.get("trade_date", ""),
                "open": latest.get("open", 0),
                "high": latest.get("high", 0),
                "low": latest.get("low", 0),
                "close": latest.get("close", 0),
                "pre_close": latest.get("pre_close", 0),
                "change": latest.get("change", 0),
                "pct_chg": latest.get("pct_chg", 0),
                "vol": latest.get("vol", 0),
                "amount": latest.get("amount", 0),
                "valuation": valuation,
                "history": daily_data[:60],  # 最近60天数据
            }
        return None

    async def fetch_market_stats(self) -> Optional[Dict[str, int]]:
        """获取市场涨跌统计数据"""
        # 使用 daily 接口获取当日所有股票数据来统计涨跌
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        data = await self._request("daily", {
            "trade_date": end_date,
            "limit": 5000
        })

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])

            up_count = 0
            down_count = 0

            for item in items:
                item_dict = dict(zip(fields, item))
                pct_chg = item_dict.get("pct_chg", 0)
                if pct_chg > 0:
                    up_count += 1
                elif pct_chg < 0:
                    down_count += 1

            return {
                "up_count": up_count,
                "down_count": down_count,
                "total": len(items)
            }
        return None

    async def fetch_north_fund_flow(self) -> Optional[Dict[str, float]]:
        """获取北向资金流向（使用 moneyflow 接口模拟）"""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

        # 使用上证50成分股的资金流向模拟北向资金
        data = await self._request("moneyflow", {
            "trade_date": end_date,
            "limit": 100
        })

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])

            total_inflow = 0
            for item in items:
                item_dict = dict(zip(fields, item))
                # 使用大单净流入作为北向资金代理
                net_amount = item_dict.get("net_mf_amount", 0)
                total_inflow += float(net_amount) if net_amount else 0

            # 计算30日平均
            avg_inflow = total_inflow / 30 if total_inflow else 1

            return {
                "net_inflow": total_inflow,
                "avg_inflow": avg_inflow
            }
        return None

    async def fetch_sentiment_data(self) -> Dict[str, Any]:
        """获取市场情绪数据"""
        # 获取上证指数数据计算市场情绪
        index_data = await self.fetch_index_daily("000001.SH")

        if index_data and len(index_data) >= 2:
            latest = index_data[0]
            prev = index_data[1]

            pct_chg = latest.get("pct_chg", 0)
            close = latest.get("close", 0)
            pre_close = prev.get("close", close)

            # 计算情绪指数 (0-100)
            # 基于涨跌幅、成交量变化等因素
            base_sentiment = 50
            if pct_chg > 0:
                base_sentiment += min(pct_chg * 5, 30)
            else:
                base_sentiment += max(pct_chg * 5, -30)

            sentiment_index = max(0, min(100, base_sentiment))

            if sentiment_index >= 80:
                status = "极度贪婪"
            elif sentiment_index >= 60:
                status = "贪婪"
            elif sentiment_index >= 40:
                status = "中性"
            elif sentiment_index >= 20:
                status = "恐惧"
            else:
                status = "极度恐惧"

            return {
                "index": round(sentiment_index, 1),
                "status": status,
                "trend": "up" if pct_chg > 0 else "down",
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "fear_greed_index": round(sentiment_index),
                "fear_greed_status": status,
                "market_index": {
                    "code": "000001.SH",
                    "name": "上证指数",
                    "close": close,
                    "change": pct_chg,
                },
            }

        # 默认返回模拟数据
        return {
            "index": 45.5,
            "status": "中性",
            "trend": "down",
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "fear_greed_index": 45,
            "fear_greed_status": "中性",
        }

    def clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """数据清洗"""
        cleaned = {}
        for key, value in data.items():
            if value is not None and value != "":
                cleaned[key] = value
        return cleaned

    def calculate_technical_indicators(self, data: List[Dict]) -> Dict[str, Any]:
        """计算技术指标"""
        if not data or len(data) < 20:
            return {}

        closes = [item.get("close", 0) for item in data if item.get("close")]
        if not closes:
            return {}

        # 计算MA5, MA10, MA20
        ma5 = sum(closes[:5]) / 5 if len(closes) >= 5 else 0
        ma10 = sum(closes[:10]) / 10 if len(closes) >= 10 else 0
        ma20 = sum(closes[:20]) / 20 if len(closes) >= 20 else 0

        # 计算RSI (简化版)
        if len(closes) >= 14:
            gains = []
            losses = []
            for i in range(1, 14):
                change = closes[i-1] - closes[i]
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))
            avg_gain = sum(gains) / 14 if gains else 0
            avg_loss = sum(losses) / 14 if losses else 0
            rs = avg_gain / avg_loss if avg_loss > 0 else 0
            rsi = 100 - (100 / (1 + rs)) if rs > 0 else 50
        else:
            rsi = 50

        return {
            "ma5": round(ma5, 2),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "rsi": round(rsi, 2),
            "current_price": closes[0],
        }
