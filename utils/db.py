from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models.model import Base
import os

#DATABASE_URL = "mysql+aiomysql://root:159753@localhost:3306/school_club"
#engine = create_async_engine(DATABASE_URL, echo=True)

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://root:159753@localhost:3307/school_club")
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
