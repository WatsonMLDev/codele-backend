"""Codele Backend — FastAPI Application Entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routers import calendar, problems, themes
from src.shared.db import init_db, close_db

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan: connect to MongoDB on startup, disconnect on shutdown ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Motor + Beanie on startup; close the connection on shutdown."""
    await init_db()
    yield
    await close_db()


# ── FastAPI app ──
app = FastAPI(
    title="Codele API",
    description="Backend for the Codele daily coding game.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS (allow all during development — tighten for production) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiting (5 requests/min on problem endpoints) ──
app.add_middleware(
    RateLimitMiddleware,
    rate_limit=10,
    window_seconds=60,
    protected_paths=["/api/v1/problem"],
)

# ── Register routers ──
app.include_router(problems.router)
app.include_router(calendar.router)
app.include_router(themes.router)


# ── Health check ──
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "service": "codele-api"}
