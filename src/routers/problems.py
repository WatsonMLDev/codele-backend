"""Problems router — serves daily coding problems (Tier 2: full content).

Protected by:
- Rate limiting (via middleware, 10 req/min/IP)
- Time-lock: cannot fetch problems for future dates
"""

import hashlib
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from src.models.problem import DailyProblem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/problem", tags=["Problems"])


@router.get("/today")
async def get_today_problem():
    """Return today's coding problem.

    If no problem exists for today's date, use the "Infinite Fallback"
    strategy: hash the date string to deterministically pick an existing
    problem from the database so players always have something to solve.

    Returns camelCase JSON matching the React frontend schema.
    """
    today_key = datetime.utcnow().strftime("%Y-%m-%d")

    # Try to fetch today's problem directly
    problem = await DailyProblem.get(today_key)

    if problem:
        return problem.model_dump(by_alias=True)

    # ── Infinite Fallback ──
    logger.warning("No problem for %s — activating Infinite Fallback", today_key)

    all_problems = await DailyProblem.find_all().to_list()

    if not all_problems:
        raise HTTPException(
            status_code=404,
            detail="No problems available in the database yet. "
            "Trigger generation first via POST /api/v1/admin/trigger-generation",
        )

    # Deterministic selection: hash the date and pick by index
    date_hash = int(hashlib.sha256(today_key.encode()).hexdigest(), 16)
    index = date_hash % len(all_problems)
    fallback = all_problems[index]

    logger.info(
        "Fallback selected problem '%s' (index %d of %d)",
        fallback.title,
        index,
        len(all_problems),
    )

    return {
        **fallback.model_dump(by_alias=True),
        "_fallback": True,
        "_original_date": today_key,
    }


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

    return problem.model_dump(by_alias=True)
