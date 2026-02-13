"""Codele Admin Dashboard — SSR FastAPI + Jinja2 Application.

Run with:
    uvicorn src.admin.main:app --port 8501 --reload
"""

import calendar as cal
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.shared.db import init_db, close_db
from src.shared.models.problem import DailyProblem, TestCase, WeeklyTheme

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


# ── Lifespan ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="Codele Admin", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────

async def _get_buffer_depth() -> int:
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    future = await DailyProblem.find(DailyProblem.id > today_str).to_list()
    return len(future)


async def _get_calendar_data(year: int, month: int) -> dict:
    """Build all data needed for the calendar template."""
    prefix = f"{year:04d}-{month:02d}"
    problems = await DailyProblem.find(
        DailyProblem.id >= f"{prefix}-01",
        DailyProblem.id <= f"{prefix}-31",
    ).to_list()
    problem_map = {p.id: p for p in problems}

    themes = await WeeklyTheme.find_all(sort=[("-generated_at", -1)], limit=20).to_list()

    # Assign a unique color index to each theme
    THEME_COLORS = [
        '#d29922', '#58a6ff', '#3fb950', '#f85149',
        '#bc8cff', '#79c0ff', '#e3b341', '#56d364',
    ]
    theme_color_map = {}
    color_idx = 0
    for t in themes:
        key = t.theme
        if key not in theme_color_map:
            theme_color_map[key] = THEME_COLORS[color_idx % len(THEME_COLORS)]
            color_idx += 1

    # Build date → theme lookup using date ranges
    def _find_theme_for_date(date_key: str) -> tuple:
        """Return (theme_name, theme_label, color, theme_id) for a date, or ("", "", "", None)."""
        for t in themes:
            # New-style: date range
            if t.start_date and t.end_date:
                if t.start_date <= date_key <= t.end_date:
                    label = f"{t.start_date} → {t.end_date}"
                    return t.theme, label, theme_color_map.get(t.theme, '#58a6ff'), str(t.id)
        return "", "", "", None

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    first_weekday, num_days = cal.monthrange(year, month)

    # Build flat list of all cells to detect theme boundaries
    all_cells = []
    for day in range(1, num_days + 1):
        date_key = f"{year:04d}-{month:02d}-{day:02d}"
        theme_name, theme_label, theme_clr, theme_id = _find_theme_for_date(date_key)
        all_cells.append({
            "day": day,
            "date_key": date_key,
            "is_today": date_key == today_str,
            "problem": problem_map.get(date_key),
            "theme": theme_name,
            "theme_label": theme_label,
            "theme_color": theme_clr,
            "theme_id": theme_id,
        })

    # Mark which cells are first/last in their theme group
    for i, cell in enumerate(all_cells):
        if not cell["theme"]:
            cell["theme_start"] = False
            cell["theme_end"] = False
            continue
        prev_theme = all_cells[i - 1]["theme"] if i > 0 else ""
        next_theme = all_cells[i + 1]["theme"] if i < len(all_cells) - 1 else ""
        cell["theme_start"] = cell["theme"] != prev_theme
        cell["theme_end"] = cell["theme"] != next_theme

    # Chunk into week rows
    weeks = []
    current_week = []
    for _ in range(first_weekday):
        current_week.append(None)

    for cell in all_cells:
        current_week.append(cell)
        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []

    if current_week:
        while len(current_week) < 7:
            current_week.append(None)
        weeks.append(current_week)

    buffer = await _get_buffer_depth()

    return {
        "year": year,
        "month": month,
        "month_name": cal.month_name[month],
        "weeks": weeks,
        "num_problems": len(problems),
        "num_days": num_days,
        "buffer": buffer,
        "themes": themes[:10],
    }


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def calendar_page(request: Request, year: int = None, month: int = None):
    now = datetime.utcnow()
    year = year or now.year
    month = month or now.month
    data = await _get_calendar_data(year, month)

    # Prev/next month links
    prev_date = date(year, month, 1) - timedelta(days=1)
    next_date = date(year, month, 28) + timedelta(days=4)
    next_date = next_date.replace(day=1)

    return templates.TemplateResponse("calendar.html", {
        "request": request,
        **data,
        "prev_year": prev_date.year,
        "prev_month": prev_date.month,
        "next_year": next_date.year,
        "next_month": next_date.month,
    })


@app.get("/editor/{date_key}", response_class=HTMLResponse)
async def editor_page(request: Request, date_key: str):
    problem = await DailyProblem.get(date_key)
    return templates.TemplateResponse("editor.html", {
        "request": request,
        "date_key": date_key,
        "problem": problem,
    })


@app.post("/editor/{date_key}/save")
async def save_problem(
    date_key: str,
    title: str = Form(...),
    difficulty: str = Form(...),
    description: str = Form(...),
    starter_code: str = Form(...),
    topics: str = Form(""),
    test_cases_json: str = Form("[]"),
):
    problem = await DailyProblem.get(date_key)
    if not problem:
        raise HTTPException(404, "Problem not found")

    problem.title = title
    problem.difficulty = difficulty
    problem.description = description
    problem.starter_code = starter_code
    problem.topics = [t.strip() for t in topics.split(",") if t.strip()]

    # Parse test cases from JSON
    try:
        tc_list = json.loads(test_cases_json)
        problem.test_cases = [
            TestCase(
                id=i + 1,
                type=tc.get("type", "basic"),
                input=tc.get("input", ""),
                expected=tc.get("expected", ""),
                hint=tc.get("hint", ""),
            )
            for i, tc in enumerate(tc_list)
        ]
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse test cases: %s", e)

    await problem.save()
    return RedirectResponse(f"/editor/{date_key}?saved=1", status_code=303)


@app.post("/editor/{date_key}/delete")
async def delete_problem(date_key: str):
    problem = await DailyProblem.get(date_key)
    if problem:
        await problem.delete()
    return RedirectResponse("/", status_code=303)


@app.post("/editor/{date_key}/move")
async def move_problem(date_key: str, new_date: str = Form(...)):
    problem = await DailyProblem.get(date_key)
    if not problem:
        raise HTTPException(404, "Problem not found")

    # Validate new date
    try:
        datetime.strptime(new_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Invalid date format")

    # Check target is empty
    existing = await DailyProblem.get(new_date)
    if existing:
        raise HTTPException(409, f"Date {new_date} already has a problem")

    # Create new doc with new ID, delete old
    data = problem.model_dump(by_alias=True)
    data.pop("_id", None)
    data.pop("id", None)
    new_problem = DailyProblem(id=new_date, **data)
    await new_problem.insert()
    await problem.delete()

    return RedirectResponse(f"/editor/{new_date}?moved=1", status_code=303)


@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request, year: int = None, month: int = None):
    from src.shared.services.content_engine import _find_next_open_date

    buffer = await _get_buffer_depth()
    next_open = await _find_next_open_date()
    next_open_str = next_open.strftime("%Y-%m-%d")

    # Default to the month of the next open date
    year = year or next_open.year
    month = month or next_open.month

    # Get data for prompt preview
    recent_themes_docs = await WeeklyTheme.find_all(
        sort=[("-generated_at", -1)], limit=10
    ).to_list()
    recent_themes = [t.theme for t in recent_themes_docs]

    all_problems = await DailyProblem.find_all().to_list()
    existing_titles = [p.title for p in all_problems]
    scheduled_dates = [p.id.isoformat() if hasattr(p.id, "isoformat") else p.id for p in all_problems]  # dates as strings

    # Prev/next month links
    prev_date = date(year, month, 1) - timedelta(days=1)
    next_date = date(year, month, 28) + timedelta(days=4)
    next_date = next_date.replace(day=1)

    return templates.TemplateResponse("generate.html", {
        "request": request,
        "buffer": buffer,
        "year": year,
        "month": month,
        "month_name": cal.month_name[month],
        "prev_year": prev_date.year,
        "prev_month": prev_date.month,
        "next_year": next_date.year,
        "next_month": next_date.month,
        "next_open_date": next_open_str,
        "recent_themes": recent_themes,
        "existing_titles": existing_titles,
        "existing_count": len(existing_titles),
        "scheduled_dates": scheduled_dates,
    })


@app.post("/api/generate")
async def api_generate_batches(request: Request):
    """Process multiple generation batches sequentially.

    Each batch's auto-theme call will see all previously generated themes,
    preventing the AI from picking duplicate themes within a single plan.
    """
    from src.shared.services.content_engine import generate_batch

    body = await request.json()
    batches = body.get("batches", [])
    if not batches:
        raise HTTPException(400, "No batches provided")

    results = []
    for i, batch_def in enumerate(batches):
        start_str = batch_def.get("start_date", "")
        count = batch_def.get("count", 7)
        theme = batch_def.get("theme", "")

        try:
            parsed_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            results.append({"batch": i + 1, "error": f"Invalid date: {start_str}"})
            continue

        try:
            result = await generate_batch(
                start_date=parsed_date,
                count=count,
                theme=theme if theme.strip() else None,
            )
            logger.info("Batch %d generated: %s", i + 1, result)
            results.append({"batch": i + 1, **result})
        except Exception as e:
            logger.exception("Batch %d failed", i + 1)
            results.append({"batch": i + 1, "error": str(e)})

    total = sum(r.get("problems_created", 0) for r in results)
    return {"results": results, "total_created": total}



class ThemeUpdateRequest(BaseModel):
    theme_id: str
    new_theme: str


@app.post("/api/theme/update")
async def update_theme(payload: ThemeUpdateRequest):
    from beanie import PydanticObjectId
    try:
        theme = await WeeklyTheme.get(PydanticObjectId(payload.theme_id))
        if not theme:
            raise HTTPException(status_code=404, detail="Theme not found")
        
        theme.theme = payload.new_theme
        await theme.save()
        return {"status": "success", "theme": theme.theme}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── API endpoint for drag-and-drop moves (AJAX) ──
@app.post("/api/move")
async def api_move_problem(request: Request):
    body = await request.json()
    from_date = body.get("from_date")
    to_date = body.get("to_date")

    if not from_date or not to_date:
        raise HTTPException(400, "Missing from_date or to_date")

    problem = await DailyProblem.get(from_date)
    if not problem:
        raise HTTPException(404, f"No problem on {from_date}")

    existing = await DailyProblem.get(to_date)
    if existing:
        raise HTTPException(409, f"Date {to_date} already has a problem")

    data = problem.model_dump(by_alias=True)
    data.pop("_id", None)
    data.pop("id", None)
    new_problem = DailyProblem(id=to_date, **data)
    await new_problem.insert()
    await problem.delete()

    return {"status": "ok", "from": from_date, "to": to_date}
