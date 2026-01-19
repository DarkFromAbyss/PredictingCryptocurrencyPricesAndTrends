import httpx
import pandas as pd
import logging
from datetime import datetime
from .config import settings

logger = logging.getLogger(__name__)

class BinanceLoader:
    def __init__(self):
        self.base_url = "https://data-api.binance.vision/api/v3"

    def _date_to_ms(self, date_str: str) -> int:
        """Chuyển đổi ngày (VD: '2023-01-01') sang mili-giây."""
        try:
            dt = pd.to_datetime(date_str)
            return int(dt.timestamp() * 1000)
        except Exception:
            return None

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 1000, 
                          start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Tải dữ liệu có hỗ trợ khoảng thời gian (Start - End).
        """
        clean_symbol = symbol.replace('/', '').replace('-', '').upper()
        url = f"{self.base_url}/klines"
        
        # Cấu hình tham số gửi đi
        params = {
            "symbol": clean_symbol,
            "interval": timeframe,
            "limit": limit
        }

        # Nếu người dùng nhập ngày bắt đầu -> Thêm vào params
        if start_date:
            ms = self._date_to_ms(start_date)
            if ms:
                params["startTime"] = ms
        
        # Nếu người dùng nhập ngày kết thúc -> Thêm vào params
        if end_date:
            ms = self._date_to_ms(end_date)
            if ms:
                params["endTime"] = ms

        try:
            logger.info(f"🔄 Đang tải {clean_symbol} | Từ: {start_date} -> Đến: {end_date} ...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"⚠️ Lỗi API: {response.status_code} - {response.text}")
                    return pd.DataFrame()

                klines = response.json()
                if not klines:
                    logger.warning(f"⚠️ Không có dữ liệu trong khoảng thời gian này.")
                    return pd.DataFrame()

                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                    'close_time', 'q_vol', 'trades', 'tb_base', 'tb_quote', 'ignore'
                ])
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # Chuyển đổi số liệu
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                df[numeric_cols] = df[numeric_cols].astype(float)
                
                logger.info(f"✅ Tải thành công: {len(df)} dòng.")
                return df

        except Exception as e:
            logger.error(f"❌ Lỗi kết nối: {e}")
            return pd.DataFrame()