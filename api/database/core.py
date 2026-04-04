from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from api.config import get_api_settings

_settings = get_api_settings()

engine = create_async_engine(
    _settings.database_url, echo=False
)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

Base = declarative_base()

# Dependency
async def get_db():
    async with SessionLocal() as db:
        yield db
