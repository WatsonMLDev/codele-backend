"""Beanie document models for the Codele database."""

from datetime import datetime
from typing import List, Optional

from beanie import Document
from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """A single test case for a coding problem."""

    input: str = Field(..., description="Input to pass to the solution function")
    expected_output: str = Field(..., description="Expected output from the solution")
    is_conciseness_check: bool = Field(
        default=False,
        description="If True, this test checks solution length instead of correctness",
    )
    max_lines: Optional[int] = Field(
        default=None,
        description="Maximum allowed lines of code (only used when is_conciseness_check=True)",
    )


class DailyProblem(Document):
    """A single daily coding problem served to players."""

    id: str = Field(
        ...,
        description="Date key in YYYY-MM-DD format, e.g. '2026-02-12'",
    )
    title: str = Field(..., description="Human-readable problem title")
    difficulty: str = Field(
        ..., description="Difficulty level: 'Easy', 'Medium', or 'Hard'"
    )
    description: str = Field(
        ..., description="Full problem description in Markdown"
    )
    starter_code: str = Field(
        ..., description="Boilerplate code given to the player"
    )
    test_cases: List[TestCase] = Field(
        default_factory=list, description="List of test cases"
    )
    topics: List[str] = Field(
        default_factory=list,
        description="Tags like 'Two Pointers', 'Dynamic Programming'",
    )
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Vector embedding for semantic search (e.g. 768-dim)",
    )

    class Settings:
        name = "daily_problems"


class WeeklyTheme(Document):
    """Tracks the theme chosen for each week's problem batch."""

    week_id: str = Field(
        ...,
        description="ISO week key, e.g. '2026-W07'",
    )
    theme: str = Field(..., description="The coding topic for this week")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this batch was generated",
    )

    class Settings:
        name = "weekly_themes"
