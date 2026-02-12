"""Codele Backend — FastAPI Application Entrypoint."""

import logging
import os
from contextlib import asynccontextmanager

from beanie import init_beanie
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from src.models.problem import DailyProblem, WeeklyTheme
from src.routers import admin, problems

# ── Load environment variables ──
load_dotenv()

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
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "codele")

    logger.info("Connecting to MongoDB (db=%s)…", db_name)
    client = AsyncIOMotorClient(mongo_uri)

    await init_beanie(
        database=client[db_name],
        document_models=[DailyProblem, WeeklyTheme],
    )
    logger.info("Beanie initialized — database ready.")

    yield  # app is running

    client.close()
    logger.info("MongoDB connection closed.")


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

# ── Register routers ──
app.include_router(problems.router)
app.include_router(admin.router)


# ── Health check ──
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "service": "codele-api"}
