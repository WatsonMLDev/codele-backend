"""Codele Backend — FastAPI Application Entrypoint."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import calendar, problems, themes
from src.shared.db import init_db, close_db
from src.shared.config import load_config
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.middleware.security import SecurityHeadersMiddleware
from src.api.middleware.api_key import APIKeyValidationMiddleware

# ── Configuration ──
config = load_config()

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format=config.logging.get("format", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"),
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
env = os.getenv("ENV", "development")
is_prod = env == "production"

app = FastAPI(
    title=config.project.get("name", "Codele API"),
    description=config.project.get("description", "Backend for the Codele daily coding game."),
    version=config.project.get("version", "0.1.0"),
    lifespan=lifespan,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json"
)

# ── CORS (allow all during development — tighten for production) ──
allowed_origins = config.cors.get("allowed_origins", ["*"])
if is_prod:
    # In production, only allow specific domains, not localhost
    allowed_origins = [o for o in allowed_origins if "localhost" not in o and "127.0.0.1" not in o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom security middlewares (Order matters: executed bottom-to-top)
app.add_middleware(APIKeyValidationMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(SecurityHeadersMiddleware)



# ── Register routers ──
app.include_router(problems.router)
app.include_router(calendar.router)
app.include_router(themes.router)


# ── Health check ──
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "service": "codele-api"}
