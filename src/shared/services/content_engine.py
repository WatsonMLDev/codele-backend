"""Content Engine — orchestrates AI-powered problem generation.

The LLM generates pure problems (no dates). This engine:
1. Finds the next available date slot in the database.
2. Calls BAML to generate N problems for a theme.
3. Assigns dates and difficulties programmatically, then bulk-inserts.

Themes are fully flexible — algorithmic topics, holiday themes,
semantic concepts, or anything else.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from src.shared.models.problem import DailyProblem, TestCase, WeeklyTheme

logger = logging.getLogger(__name__)

# Base difficulty cycle — repeats for any batch size
DIFFICULTY_CYCLE = [
    "Easy",    # 1
    "Easy",    # 2
    "Medium",  # 3
    "Medium",  # 4
    "Hard",    # 5
    "Hard",    # 6
    "Medium",  # 7
]


def get_difficulty_sequence(count: int) -> list[str]:
    """Build a difficulty list for any count by cycling through the pattern."""
    return [DIFFICULTY_CYCLE[i % len(DIFFICULTY_CYCLE)] for i in range(count)]


async def _find_next_open_date() -> date:
    """Find the day after the latest scheduled problem in the DB.

    Unlike the old version (which scanned from 'today'), this always
    appends after the last scheduled date — preventing week-cycle drift
    if generation is triggered late.
    """
    latest = await DailyProblem.find_all(
        sort=[("-_id", -1)], limit=1
    ).to_list()

    if latest:
        last_date = datetime.strptime(latest[0].id, "%Y-%m-%d").date()
        return last_date + timedelta(days=1)

    # Empty DB — start from today
    return datetime.utcnow().date()


async def _pick_theme(force_theme: Optional[str] = None) -> str:
    """Pick a theme — either forced or AI-selected avoiding recent repeats."""
    if force_theme:
        return force_theme

    from src.baml_client.baml_client.async_client import b  # type: ignore[import-untyped]

    recent_themes_docs = await WeeklyTheme.find_all(
        sort=[("-generated_at", -1)],
        limit=10,
    ).to_list()
    recent_theme_names = [t.theme for t in recent_themes_docs]
    logger.info("Recent themes to avoid: %s", recent_theme_names)

    theme = await b.PickWeeklyTheme(recent_themes=recent_theme_names)
    return theme.strip()


async def _build_problems(
    batch: list,
    start_date: date,
    count: int,
) -> list[DailyProblem]:
    """Convert BAML output schemas into DailyProblem documents with dates."""
    difficulties = get_difficulty_sequence(count)
    problems = []
    current_date = start_date

    for i, schema in enumerate(batch):
        mapped_cases = []
        for idx, tc in enumerate(schema.test_cases):
            mapped_cases.append(
                TestCase(
                    id=idx + 1,
                    type=tc.type.lower(),
                    hint=tc.hint,
                    input=tc.input,
                    expected=tc.expected,
                )
            )

        date_key = current_date.strftime("%Y-%m-%d")
        difficulty = difficulties[i]

        problem = DailyProblem(
            id=date_key,
            title=schema.title,
            difficulty=difficulty,
            description=schema.description,
            starterCode=schema.starter_code,
            testCases=mapped_cases,
            topics=schema.topics,
        )
        problems.append(problem)
        current_date += timedelta(days=1)

        logger.info(
            "  [%s] %s (%s) — %d test cases",
            date_key, schema.title, difficulty, len(mapped_cases),
        )

    return problems


async def generate_batch(
    start_date: Optional[date] = None,
    count: int = 7,
    theme: Optional[str] = None,
) -> dict:
    """Generate and save a batch of coding problems.

    Args:
        start_date: First date to schedule. If None, auto-detects next open slot.
        count:      Number of problems to generate (any positive integer).
        theme:      Force a specific theme. If None, AI picks one.

    Returns:
        Summary dict with theme, count, and date range.
    """
    from src.baml_client.baml_client.async_client import b  # type: ignore[import-untyped]

    # ── 1. Determine start date ──
    if start_date is None:
        start_date = await _find_next_open_date()

    start_str = start_date.strftime("%Y-%m-%d")
    end_date = start_date + timedelta(days=count - 1)
    end_str = end_date.strftime("%Y-%m-%d")

    logger.info(
        "Generating %d problems: %s → %s",
        count, start_str, end_str,
    )

    # ── 2. Pick theme ──
    chosen_theme = await _pick_theme(force_theme=theme)
    logger.info("Theme: %s", chosen_theme)

    # ── 3. Get existing titles for deduplication ──
    existing_problems = await DailyProblem.find_all().to_list()
    existing_titles = [p.title for p in existing_problems]
    logger.info("Existing titles count: %d", len(existing_titles))

    # ── 4. Generate via BAML ──
    batch = await b.GenerateProblemBatch(
        theme=chosen_theme,
        count=count,
        existing_titles=existing_titles,
    )
    logger.info("AI generated %d problems", len(batch))

    # ── 5. Build documents ──
    problems = await _build_problems(batch, start_date, count)

    # ── 6. Bulk-insert into MongoDB ──
    await DailyProblem.insert_many(problems)
    logger.info("Inserted %d problems into MongoDB", len(problems))

    # ── 7. Save theme record with date range ──
    theme_record = WeeklyTheme(
        theme=chosen_theme,
        start_date=start_str,
        end_date=end_str,
        count=len(problems),
        generated_at=datetime.utcnow(),
    )
    await theme_record.insert()
    logger.info("Saved theme: %s (%s → %s)", chosen_theme, start_str, end_str)

    return {
        "theme": chosen_theme,
        "problems_created": len(problems),
        "date_range": f"{start_str} → {end_str}",
    }


async def get_buffer_depth() -> int:
    """Return the number of days of content scheduled beyond today."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    future_problems = await DailyProblem.find(
        DailyProblem.id > today_str
    ).to_list()
    return len(future_problems)


# ── Legacy alias for backwards compatibility ──
generate_next_week = generate_batch
