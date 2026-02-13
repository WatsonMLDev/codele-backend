"""Problems router — serves daily coding problems (Tier 2: full content).

Protected by:
- Rate limiting (via middleware, 10 req/min/IP)
- Time-lock: cannot fetch problems for future dates

Adapter Pattern: transforms Beanie output to be byte-for-byte compatible
with the React frontend, without any frontend changes.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from src.shared.models.problem import DailyProblem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/problem", tags=["Problems"])


def _adapt_for_frontend(data: dict) -> dict:
    """Transform a Beanie-serialized problem dict for exact frontend compatibility.

    1. Rename '_id' → 'id'  (MongoDB uses _id; React expects id)
    2. Remove 'embedding'   (internal field, not needed by frontend)
    """
    # ── 1. _id → id ──
    if "_id" in data:
        data["id"] = data.pop("_id")

    # ── 2. Strip embedding ──
    data.pop("embedding", None)

    return data


@router.get("/today")
async def get_today_problem():
    """Return today's coding problem.

    Returns camelCase JSON matching the React frontend schema.
    If no problem exists for today, returns 404.
    """
    today_key = datetime.utcnow().strftime("%Y-%m-%d")

    problem = await DailyProblem.get(today_key)

    if not problem:
        raise HTTPException(
            status_code=404,
            detail=f"No problem available for {today_key}.",
        )

    return _adapt_for_frontend(problem.model_dump(by_alias=True))


@router.get("/{date}")
async def get_problem_by_date(date: str):
    """Return a specific problem by date.

    Time-locked: cannot fetch problems for future dates.
    """
    # Validate date format
    try:
        requested = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    # ── Time-Lock: block future dates ──
    today = datetime.utcnow()
    if requested.date() > today.date():
        raise HTTPException(
            status_code=403,
            detail="Cannot access problems for future dates.",
        )

    # Fetch the problem
    problem = await DailyProblem.get(date)

    if not problem:
        raise HTTPException(
            status_code=404,
            detail=f"No problem found for {date}.",
        )

    return _adapt_for_frontend(problem.model_dump(by_alias=True))
