import pandas as pd
import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, func
from .models import Candle

class CandleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_upsert(self, df: pd.DataFrame, symbol: str, timeframe: str, chunk_size: int = 5000) -> int:
        """
        Lưu dữ liệu vào DB theo từng lô nhỏ (Chunking) để tránh sập kết nối.
        """
        if df.empty:
            return 0

        # 1. Chuẩn bị dữ liệu
        # Đảm bảo không có giá trị NaN (Pandas NaN -> Python None cho SQL)
        df = df.where(pd.notnull(df), None)
        
        # Chuyển DataFrame thành list các dictionary
        records = df.to_dict(orient='records')
        
        # Gán thêm symbol và timeframe cho mỗi dòng
        for record in records:
            record['symbol'] = symbol
            record['timeframe'] = timeframe

        total_inserted = 0
        total_records = len(records)
        
        # 2. Chia nhỏ và gửi lần lượt (Batch Processing)
        # Tính toán số lượng lô cần gửi
        num_chunks = math.ceil(total_records / chunk_size)
        
        print(f"📦 Đang lưu {total_records} dòng (Chia thành {num_chunks} lô)...")

        for i in range(0, total_records, chunk_size):
            chunk = records[i : i + chunk_size]
            
            # Câu lệnh UPSERT của PostgreSQL (Insert if not exists, else Update)
            stmt = insert(Candle).values(chunk)
            
            # Nếu trùng khóa chính (hoặc Unique Constraint), cập nhật lại giá trị
            # Giả sử bạn có Unique Index trên (symbol, timeframe, timestamp)
            # Ở đây ta dùng 'do_update' để ghi đè dữ liệu cũ bằng dữ liệu mới
            update_stmt = stmt.on_conflict_do_update(
                index_elements=['symbol', 'timeframe', 'timestamp'], # Cần đảm bảo Model có UniqueConstraint này
                set_={
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'close': stmt.excluded.close,
                    'volume': stmt.excluded.volume
                }
            )
            
            try:
                await self.db.execute(update_stmt)
                await self.db.commit() # Lưu ngay lập tức sau mỗi lô
                total_inserted += len(chunk)
                print(f"   ✅ Đã lưu lô {i//chunk_size + 1}/{num_chunks}")
            except Exception as e:
                await self.db.rollback()
                print(f"   ❌ Lỗi lưu lô {i//chunk_size + 1}: {e}")
                # Tùy chọn: raise e nếu muốn dừng ngay lập tức

        return total_inserted