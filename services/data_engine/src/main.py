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
    limit: int = 1000,
    start_date: Optional[str] = None, # Ví dụ: 2023-01-01
    end_date: Optional[str] = None,   # Ví dụ: 2023-02-01
    db: AsyncSession = Depends(get_db)
):
    """
    Tải dữ liệu crypto. Có thể chỉ định ngày bắt đầu và kết thúc.
    Format ngày: YYYY-MM-DD (Ví dụ: 2024-01-01)
    """
    formatted_symbol = symbol.replace("-", "/").upper()
    
    loader = BinanceLoader()
    # Truyền thêm start_date và end_date vào hàm
    df = await loader.fetch_ohlcv(formatted_symbol, timeframe, limit, start_date, end_date)
    
    if df.empty:
        return {"status": "error", "message": "No data fetched or empty range"}

    repo = CandleRepository(db)
    count = await repo.bulk_upsert(df, formatted_symbol, timeframe)
    
    return {
        "status": "success",
        "symbol": formatted_symbol,
        "timeframe": timeframe,
        "data_range": {
            "start": str(df['timestamp'].min()),
            "end": str(df['timestamp'].max())
        },
        "rows_inserted": count
    }

@app.get("/api/v1/debug/count")
async def count_candles(db: AsyncSession = Depends(get_db)):
    """API to check how many rows are in the database"""
    from sqlalchemy import text
    result = await db.execute(text("SELECT COUNT(*) FROM candles"))
    count = result.scalar()
    return {"total_candles": count}