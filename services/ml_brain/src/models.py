from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)