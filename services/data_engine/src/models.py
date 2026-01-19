from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Candle(Base):
    __tablename__ = "candles"

    # Self-generated primary key
    id = Column(Integer, primary_key=True, index=True)
    
    symbol = Column(String(20), index=True, nullable=False)    # E.g: BTC/USDT
    timeframe = Column(String(10), index=True, nullable=False) # E.g: 1h, 1d
    timestamp = Column(DateTime, index=True, nullable=False)   # Candle timestamp   
    
    # \--- Candle data fields ---
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    # Unique constraint to avoid duplicate candles for the same symbol, timeframe, and timestamp    
    # Ensures no two candles exist with the same symbol, timeframe, and timestamp
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uix_candle_identity'),
    )