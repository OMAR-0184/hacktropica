from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from arq import create_pool
from arq.connections import RedisSettings

from api.config import get_api_settings
from api.database.core import Base, engine
from api.database import models as _db_models  # noqa: F401
from api.routers import auth, learning, search

_settings = get_api_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bootstrap schema for local/dev environments without Alembic setup.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Create the ARQ Redis pool
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(_settings.redis_url))
    yield
    # Close ARQ connections on shutdown
    await app.state.arq_pool.aclose()


app = FastAPI(
    title="Cognimap API",
    description="Adaptive Learning System Gateway powered by LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(learning.router, prefix="/learning", tags=["Learning"])
app.include_router(search.router, prefix="/learning", tags=["Search"])


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Cognimap Engine is running."}
