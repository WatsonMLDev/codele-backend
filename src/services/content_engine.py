"""Content Engine — orchestrates AI-powered problem generation."""

import logging
from datetime import datetime, timedelta

from src.models.problem import DailyProblem, TestCase, WeeklyTheme

logger = logging.getLogger(__name__)


async def generate_next_week() -> dict:
    """Generate a full week of coding problems using BAML AI agents.

    Flow:
        1. Query recent themes to avoid repetition.
        2. Call BAML PickWeeklyTheme to choose a fresh topic.
        3. Query existing titles for negative RAG (deduplication).
        4. Call BAML GenerateProblemBatch to produce 7 problems.
        5. Bulk-insert problems and theme into MongoDB via Beanie.

    Returns:
        Summary dict with week_id, theme, and count of problems created.
    """
    # ── Lazy import of the BAML async client ──
    # The baml_client is generated code; importing at call-time avoids
    # import errors when the client hasn't been generated yet.
    from src.baml_client.baml_client.async_client import b  # type: ignore[import-untyped]

    # ── 1. Determine the target week ──
    today = datetime.utcnow()
    # Find next Monday
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # always target *next* Monday
    next_monday = today + timedelta(days=days_until_monday)
    iso_year, iso_week, _ = next_monday.isocalendar()
    week_id = f"{iso_year}-W{iso_week:02d}"
    start_date = next_monday.strftime("%Y-%m-%d")

    logger.info("Generating problems for week %s (starting %s)", week_id, start_date)

    # ── 2. Get recent themes to avoid repetition ──
    recent_themes_docs = await WeeklyTheme.find_all(
        sort=[("-generated_at", -1)],
        limit=10,
    ).to_list()
    recent_theme_names = [t.theme for t in recent_themes_docs]
    logger.info("Recent themes to avoid: %s", recent_theme_names)

    # ── 3. Pick a fresh theme via BAML ──
    theme = await b.PickWeeklyTheme(recent_themes=recent_theme_names)
    theme = theme.strip()
    logger.info("AI picked theme: %s", theme)

    # ── 4. Get existing titles for negative RAG ──
    existing_problems = await DailyProblem.find_all().to_list()
    existing_titles = [p.title for p in existing_problems]
    logger.info("Existing titles count: %d", len(existing_titles))

    # ── 5. Generate the batch via BAML ──
    batch = await b.GenerateProblemBatch(
        theme=theme,
        start_date=start_date,
        existing_titles=existing_titles,
    )
    logger.info("AI generated %d problems", len(batch))

    # ── 6. Convert BAML output → Beanie documents ──
    problems = []
    for schema in batch:
        problem = DailyProblem(
            id=schema.id,
            title=schema.title,
            difficulty=schema.difficulty,
            description=schema.description,
            starter_code=schema.starter_code,
            test_cases=[
                TestCase(
                    input=tc.input,
                    expected_output=tc.expected_output,
                    is_conciseness_check=tc.is_conciseness_check,
                    max_lines=tc.max_lines,
                )
                for tc in schema.test_cases
            ],
            topics=schema.topics,
        )
        problems.append(problem)

    # ── 7. Bulk-insert into MongoDB ──
    await DailyProblem.insert_many(problems)
    logger.info("Inserted %d problems into MongoDB", len(problems))

    # Save the theme record
    weekly_theme = WeeklyTheme(
        week_id=week_id,
        theme=theme,
        generated_at=datetime.utcnow(),
    )
    await weekly_theme.insert()
    logger.info("Saved WeeklyTheme: %s", week_id)

    return {
        "week_id": week_id,
        "theme": theme,
        "problems_created": len(problems),
        "start_date": start_date,
    }
