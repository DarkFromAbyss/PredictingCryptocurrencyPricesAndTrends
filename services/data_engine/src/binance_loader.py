import httpx
import pandas as pd
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

# Cấu hình logging
logger = logging.getLogger(__name__)

class BinanceLoader:
    def __init__(self):
        # Sử dụng Server Vision (Dữ liệu lịch sử, không bị chặn IP)
        self.base_url = "https://data-api.binance.vision/api/v3"

    def _date_to_ms(self, date_str: str) -> int:
        """Chuyển đổi ngày (VD: '2020-01-01') sang mili-giây."""
        try:
            dt = pd.to_datetime(date_str)
            return int(dt.timestamp() * 1000)
        except Exception:
            return None

    async def fetch_ohlcv(self, symbol: str, timeframe: str, start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Hàm thông minh: Tự động lặp để tải lượng dữ liệu khổng lồ (Pagination).
        """
        clean_symbol = symbol.replace('/', '').replace('-', '').upper()
        url = f"{self.base_url}/klines"
        
        # 1. Xác định mốc thời gian
        current_start_ms = self._date_to_ms(start_date)
        if not current_start_ms:
            logger.error("❌ Phải cung cấp ngày bắt đầu (start_date) hợp lệ!")
            return pd.DataFrame()

        end_ms = self._date_to_ms(end_date) if end_date else int(datetime.now().timestamp() * 1000)
        
        all_dfs = [] # Danh sách chứa các mảnh dữ liệu
        total_fetched = 0
        limit_per_call = 1000 # Max của Binance Vision

        logger.info(f"🚀 Bắt đầu chiến dịch tải dữ liệu lớn cho {clean_symbol}...")
        logger.info(f"⏳ Từ: {start_date} -> Đến: {end_date or 'Hôm nay'}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                # Nếu thời gian bắt đầu đã vượt quá thời gian kết thúc -> Dừng
                if current_start_ms >= end_ms:
                    break

                params = {
                    "symbol": clean_symbol,
                    "interval": timeframe,
                    "limit": limit_per_call,
                    "startTime": current_start_ms,
                    "endTime": end_ms
                }

                try:
                    response = await client.get(url, params=params)
                    if response.status_code != 200:
                        logger.warning(f"⚠️ Lỗi API tại mốc {current_start_ms}: {response.status_code}")
                        break

                    klines = response.json()
                    if not klines:
                        break # Hết dữ liệu

                    # Xử lý dữ liệu thô
                    df_chunk = pd.DataFrame(klines, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                        'close_time', 'q_vol', 'trades', 'tb_base', 'tb_quote', 'ignore'
                    ])
                    df_chunk = df_chunk[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                    
                    # Chuyển đổi kiểu dữ liệu
                    df_chunk['timestamp'] = pd.to_datetime(df_chunk['timestamp'], unit='ms')
                    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                    df_chunk[numeric_cols] = df_chunk[numeric_cols].astype(float)

                    all_dfs.append(df_chunk)
                    total_fetched += len(df_chunk)
                    
                    # Lấy thời gian đóng nến của cây cuối cùng + 1ms để làm mốc bắt đầu cho vòng sau
                    last_close_time = klines[-1][6] # Cột index 6 là Close Time
                    current_start_ms = last_close_time + 1
                    
                    print(f"   --> Đã tải: {total_fetched} nến... (Mốc tiếp theo: {datetime.fromtimestamp(current_start_ms/1000)})")
                    
                    # Nghỉ 0.1 giây để không bị Binance chặn (Rate Limit)
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"❌ Lỗi trong quá trình tải: {e}")
                    break

        if not all_dfs:
            return pd.DataFrame()

        # Ghép tất cả các mảnh lại thành 1 DataFrame khổng lồ
        final_df = pd.concat(all_dfs, ignore_index=True)
        
        # Xóa trùng lặp (nếu có)
        final_df.drop_duplicates(subset=['timestamp'], inplace=True)
        
        logger.info(f"✅ HOÀN TẤT! Tổng cộng đã tải: {len(final_df)} dòng dữ liệu.")
        return final_df