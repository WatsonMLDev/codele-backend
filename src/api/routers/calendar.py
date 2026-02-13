"""Calendar router — lightweight public endpoint for month views.

Returns only dates and difficulty levels, no problem content.
This is the "Tier 1" API designed to be safe to expose publicly.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Query

from src.shared.models.problem import DailyProblem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/calendar", tags=["Calendar"])


@router.get("")
async def get_month_calendar(
    month: str = Query(
        ...,
        pattern=r"^\d{4}-\d{2}$",
        description="Month in YYYY-MM format, e.g. '2026-02'",
        examples=["2026-02"],
    ),
):
    """Return a lightweight calendar view for the given month.

    Returns only date, difficulty, and whether a problem exists —
    NO titles, descriptions, or code. Safe to expose publicly.
    """
    # Parse and validate the month
    try:
        year, month_num = month.split("-")
        year, month_num = int(year), int(month_num)
        if not (1 <= month_num <= 12):
            raise ValueError
    except ValueError:
        return {"error": "Invalid month format. Use YYYY-MM."}

    # Build the date range prefix for querying (e.g., "2026-02")
    prefix = f"{year:04d}-{month_num:02d}"

    # Query all problems whose ID starts with this month prefix
    # DailyProblem IDs are formatted as "YYYY-MM-DD"
    problems = await DailyProblem.find(
        DailyProblem.id >= f"{prefix}-01",
        DailyProblem.id <= f"{prefix}-31",
    ).to_list()

    # Build lightweight calendar entries — only past and today, never future
    today = datetime.utcnow().strftime("%Y-%m-%d")
    entries = []
    for p in problems:
        if p.id > today:
            continue  # never leak future problems
        entries.append(
            {
                "date": p.id,
                "title": p.title,
                "difficulty": p.difficulty,
            }
        )

    # Sort by date
    entries.sort(key=lambda e: e["date"])

    return {
        "month": month,
        "count": len(entries),
        "days": entries,
    }
