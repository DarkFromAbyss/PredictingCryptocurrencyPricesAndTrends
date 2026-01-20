import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Candle

class DataLoader:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_historical_data(self, symbol: str, timeframe: str, limit: int = 5000):
        """
        Lấy dữ liệu lịch sử nến từ cơ sở dữ liệu dưới dạng Pandas DataFrame.
        """
        # 1. Tạo câu truy vấn
        # Lấy dữ liệu sắp xếp theo thời gian tăng dần (cũ -> mới) để training
        stmt = (
            select(Candle)
            .where(Candle.symbol == symbol, Candle.timeframe == timeframe)
            .order_by(Candle.timestamp.asc()) # Cũ nhất lên đầu
            .limit(limit) # Giới hạn số lượng (tránh tràn RAM nếu data quá lớn)
        )

        # 2. Thực thi
        result = await self.session.execute(stmt)
        candles = result.scalars().all()

        if not candles:
            return pd.DataFrame()

        # 3. Chuyển đổi sang Pandas DataFrame
        data = [{
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume
        } for c in candles]

        df = pd.DataFrame(data)
        
        # Đặt timestamp làm index giúp việc xử lý chuỗi thời gian dễ hơn
        df.set_index("timestamp", inplace=True)
        
        return df