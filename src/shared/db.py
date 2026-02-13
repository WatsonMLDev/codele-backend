"""Shared MongoDB + Beanie initialization.

Used by both the FastAPI app and the Streamlit admin dashboard
so that either can connect to the same database independently.
"""

import os
import logging

from beanie import init_beanie
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from src.shared.models.problem import DailyProblem, WeeklyTheme

load_dotenv()
logger = logging.getLogger(__name__)

# Module-level client reference so callers can close it later
_client: AsyncIOMotorClient | None = None


async def init_db() -> AsyncIOMotorClient:
    """Connect to MongoDB and initialize Beanie. Returns the Motor client."""
    global _client

    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "codele")

    logger.info("Connecting to MongoDB (db=%s)…", db_name)
    _client = AsyncIOMotorClient(mongo_uri)

    await init_beanie(
        database=_client[db_name],
        document_models=[DailyProblem, WeeklyTheme],
    )
    logger.info("Beanie initialized — database ready.")
    return _client


async def close_db() -> None:
    """Close the MongoDB connection."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed.")
        _client = None
