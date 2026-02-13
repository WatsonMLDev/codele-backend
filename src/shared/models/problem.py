"""Beanie document models for the Codele database.

Uses Pydantic v2 serialization aliases so that the API outputs camelCase
keys matching the React frontend, while Python code uses snake_case.
"""

from datetime import datetime
from typing import List, Literal, Optional

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


class TestCase(BaseModel):
    """A single test case for a coding problem."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(default=0, description="Sequential test case ID (1-6)")
    type: Literal["basic", "edge", "logic", "conciseness"] = Field(
        ..., description="Category of test case"
    )
    hint: str = Field(..., description="Tooltip hint shown on failure")
    input: str = Field(..., description="Input arguments as JSON string")
    expected_output: str = Field(
        ...,
        alias="expected",
        description="Expected return value as JSON string. For conciseness tests, this is the max line count.",
    )


class DailyProblem(Document):
    """A single daily coding problem served to players."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(
        ..., description="Date key in YYYY-MM-DD format, e.g. '2026-02-12'"
    )
    title: str = Field(..., description="Human-readable problem title")
    difficulty: str = Field(
        ..., description="Difficulty level: 'Easy', 'Medium', or 'Hard'"
    )
    description: str = Field(
        ..., description="Full problem description in Markdown"
    )
    starter_code: str = Field(
        ...,
        alias="starterCode",
        description="Boilerplate code given to the player",
    )
    test_cases: List[TestCase] = Field(
        default_factory=list,
        alias="testCases",
        description="List of test cases (exactly 6)",
    )
    topics: List[str] = Field(
        default_factory=list,
        description="Tags like 'Two Pointers', 'Dynamic Programming'",
    )
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Vector embedding for semantic search",
    )

    class Settings:
        name = "daily_problems"


class WeeklyTheme(Document):
    """Tracks the theme chosen for a batch of problems.

    Themes are flexible — can span any number of days (not locked to 7).
    Can be algorithmic topics, holiday themes, semantic themes, etc.
    """

    theme: str = Field(..., description="The theme name (any topic)")
    start_date: str = Field(
        default="", description="First date in the batch, YYYY-MM-DD"
    )
    end_date: str = Field(
        default="", description="Last date in the batch, YYYY-MM-DD"
    )
    count: int = Field(
        default=7, description="Number of problems in this batch"
    )
    # Legacy field — kept for backward compatibility with existing docs
    week_id: Optional[str] = Field(
        default=None, description="ISO week key (legacy), e.g. '2026-W07'"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this batch was generated",
    )

    class Settings:
        name = "weekly_themes"
