from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings

engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    echo=False,
    pool_size=10,
    max_overflow=5
)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as session:
        yield session