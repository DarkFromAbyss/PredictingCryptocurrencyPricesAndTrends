from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings
from .models import Base

# Create a Connection Pool engine
engine = create_async_engine(
    settings.DATABASE_URL_ASYNC, # from config.py
    echo=False, # Set to True to see SQL statements in terminal (Debug)
    pool_size=20, # Max 20 connections at the same time
    max_overflow=10
)

# Session factory
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Initialize the database by creating tables."""
    async with engine.begin() as conn:
        # conn.run_sync(Base.metadata.drop_all) # Uncomment if you want to drop all and recreate
        await conn.run_sync(Base.metadata.create_all)

# Dependency Injection (FastAPI)
async def get_db():
    async with SessionLocal() as session:
        yield session