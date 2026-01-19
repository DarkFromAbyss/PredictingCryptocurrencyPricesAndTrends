import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from .models import Candle

class CandleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """
        Save multiple candlesticks to the database. 
        If a candlestick already exists (at the same time), update it with the latest price.
        """
        if df.empty:
            return 0

        # 1. Convert the DataFrame into a Dictionary list in preparation for inserting it.
        # add columns for symbol and timeframe to each row.
        records = df.copy()
        records['symbol'] = symbol
        records['timeframe'] = timeframe
        # Rename the 'timestamp' column to match the model (if necessary)
        # Assume the DataFrame already has columns 'timestamp', 'open', ... 
        
        data_to_insert = records.to_dict(orient='records')

        # 2. Create the insert statement with conflict handling
        stmt = insert(Candle).values(data_to_insert)

        # On conflict (duplicate), update the existing record
        stmt = stmt.on_conflict_do_update(
            constraint='uix_candle_identity', # the name of the unique constraint
            set_={
                'open': stmt.excluded.open,
                'high': stmt.excluded.high,
                'low': stmt.excluded.low,
                'close': stmt.excluded.close,
                'volume': stmt.excluded.volume,
            }
        )

        # 3. Execute the statement
        try:
            await self.session.execute(stmt)
            await self.session.commit()
            return len(data_to_insert)
        except Exception as e:
            await self.session.rollback()
            print(f"❌ Lỗi khi lưu DB: {e}")
            raise e