import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Query

from src.shared.models.problem import WeeklyTheme

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/themes", tags=["Themes"])


@router.get("", response_model=List[WeeklyTheme])
async def get_themes(
    month: str = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Optional month filter (YYYY-MM). If provided, returns themes active in this month.",
        examples=["2026-02"],
    ),
):
    """
    Get a list of weekly themes.
    
    - By default, returns ALL past and current themes.
    - If `month` is provided, filters to themes active in that month.
    - Future themes (starting after TODAY) are NEVER returned.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # 1. Base Criteria: Prevent Future Leakage
    # Since all themes are migrated, we rely on start_date being present and accurate.
    criteria = [WeeklyTheme.start_date <= today]
    
    # 2. Month Filter: Themes that START in this month
    if month:
        # Calculate month boundaries
        try:
            year, m = map(int, month.split("-"))
            m_start = f"{month}-01"
            if m == 12:
                next_month = f"{year+1}-01-01"
            else:
                next_month = f"{year}-{m+1:02d}-01"
            
            # Themes that START in this month
            criteria.append(WeeklyTheme.start_date >= m_start)
            criteria.append(WeeklyTheme.start_date < next_month)
        except ValueError:
            # Should be caught by regex pattern, but safe fallback
            pass

    # Execute Query
    # Beanie finds intersection of all criteria
    themes = await WeeklyTheme.find(*criteria).to_list()

    # Sort: put most recent first
    themes.sort(key=lambda t: t.start_date or "", reverse=True)

    return themes
