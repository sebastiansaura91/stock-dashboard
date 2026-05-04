"""FastAPI application entry point.

Starts the APScheduler background scheduler on startup and shuts it down
cleanly when the app exits.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    logger.info("Application startup complete")
    yield
    stop_scheduler()
    logger.info("Application shutdown complete")


app = FastAPI(title="Stock Dashboard API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restrict to Vercel domain in Railway env vars if desired
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers are imported here (after app is created to avoid circular imports)
from api.routers import watchlist, stock, screener  # noqa: E402

app.include_router(watchlist.router, prefix="/api")
app.include_router(stock.router, prefix="/api")
app.include_router(screener.router, prefix="/api")


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}
