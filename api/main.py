from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from arq import create_pool
from arq.connections import RedisSettings

from api.config import get_api_settings
from api.database.core import Base, engine
from api.database import models as _db_models  # noqa: F401
from api.engine.runner import runtime
from api.middleware.error_handler import global_exception_handler
from api.middleware.rate_limiter import RateLimitMiddleware
from api.redis import get_redis, close_redis_pool
from api.routers import auth, search
from api.routers.learning import router as learning_router

_settings = get_api_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _settings.validate_runtime()

    # Bootstrap schema for local/dev environments without Alembic setup.
    if not _settings.is_production():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Initialize the GraphRuntime (pooled checkpointer + compiled graph)
    await runtime.start()

    # Create the ARQ Redis pool
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(_settings.redis_url))

    yield

    # Shutdown
    await app.state.arq_pool.aclose()
    await runtime.stop()
    await close_redis_pool()


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

app.add_middleware(RateLimitMiddleware)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(HTTPException, global_exception_handler)
app.add_exception_handler(RequestValidationError, global_exception_handler)


app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(learning_router, prefix="/learning", tags=["Learning"])
app.include_router(search.router, prefix="/learning", tags=["Search"])


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Cognimap Engine is running."}


@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    Verifies connectivity to Postgres and Redis.
    """
    health = {"status": "ok", "postgres": "ok", "redis": "ok"}

    # Check Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
    except Exception as exc:
        health["postgres"] = f"error: {exc}"
        health["status"] = "degraded"

    # Check Redis
    try:
        redis = get_redis()
        await redis.ping()
    except Exception as exc:
        health["redis"] = f"error: {exc}"
        health["status"] = "degraded"

    status_code = 200 if health["status"] == "ok" else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(content=health, status_code=status_code)
