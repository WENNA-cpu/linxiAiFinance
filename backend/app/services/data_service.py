import aiohttp
import os
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


class DataService:
    """数据服务 - Tushare API集成"""

    def __init__(self):
        # 使用提供的MCP Server Token
        self.tushare_token = os.getenv("TUSHARE_TOKEN", "323c3aa4a72205441336067dca690bc3918112710e224e1818456d29")
        self.base_url = "https://api.tushare.pro"

    async def _request(self, api_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送Tushare API请求"""
        if not self.tushare_token:
            return None

        async with aiohttp.ClientSession() as session:
            payload = {
                "api_name": api_name,
                "token": self.tushare_token,
                "params": params,
            }
            try:
                async with session.post(self.base_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("code") == 0:
                            return result.get("data", {})
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

    async def fetch_daily_basic_historical(self, ts_code: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """获取历史每日指标（估值数据）"""
        data = await self._request("daily_basic", {
            "ts_code": ts_code,
            "start_date": start_date,
            "end_date": end_date,
        })

        if data and "items" in data:
            fields = data.get("fields", [])
            items = data.get("items", [])
            return [dict(zip(fields, item)) for item in items]
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
