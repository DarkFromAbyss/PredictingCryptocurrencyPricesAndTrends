from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from .config import settings
from .database import init_db, get_db
from .binance_loader import BinanceLoader
from .repository import CandleRepository

from typing import Optional
# --- Logic startup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Data Engine Starting...")
    await init_db() # Create tables if not exist
    yield
    print("🛑 Data Engine Stopping...")

app = FastAPI(title="Crypto Data Engine", lifespan=lifespan)

# --- API Endpoints ---
@app.post("/api/v1/sync/{symbol}")
async def sync_data(
    symbol: str, 
    timeframe: str = "1h", 
    start_date: str = "2020-01-01", # Mặc định lấy từ 2020 để có nhiều dữ liệu
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Tải dữ liệu quy mô lớn (Massive Sync).
    Mặc định lấy từ 01/01/2020 đến nay (~35,000 nến 1h, hoặc 140,000 nến 15m).
    """
    formatted_symbol = symbol.replace("-", "/").upper()
    
    loader = BinanceLoader()
    
    # Gọi hàm tải thông minh (Tự động pagination)
    df = await loader.fetch_ohlcv(formatted_symbol, timeframe, start_date, end_date)
    
    if df.empty:
        return {"status": "error", "message": "Không tải được dữ liệu nào."}

    # Lưu vào DB (Bulk Upsert)
    repo = CandleRepository(db)
    # Lưu ý: Hàm bulk_upsert cần xử lý tốt việc insert số lượng lớn
    # Nếu quá chậm, SQLAlchemy có thể đơ. Nhưng với <100k rows thì vẫn ổn.
    count = await repo.bulk_upsert(df, formatted_symbol, timeframe)
    
    return {
        "status": "success",
        "symbol": formatted_symbol,
        "timeframe": timeframe,
        "total_candles": len(df),
        "database_updated": count,
        "range": {
            "start": str(df['timestamp'].min()),
            "end": str(df['timestamp'].max())
        }
    }

@app.get("/api/v1/debug/count")
async def count_candles(db: AsyncSession = Depends(get_db)):
    """API to check how many rows are in the database"""
    from sqlalchemy import text
    result = await db.execute(text("SELECT COUNT(*) FROM candles"))
    count = result.scalar()
    return {"total_candles": count}