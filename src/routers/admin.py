"""Admin router — protected endpoints for content management."""

import logging
import os

from fastapi import APIRouter, HTTPException, Header

from src.services.content_engine import generate_next_week

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


def _verify_admin_key(key: str | None) -> None:
    """Validate the admin API key against the environment variable."""
    expected = os.getenv("ADMIN_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_API_KEY is not configured on the server.",
        )
    if key != expected:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing admin API key.",
        )


@router.post("/trigger-generation")
async def trigger_generation(x_admin_key: str | None = Header(default=None)):
    """Manually trigger the weekly problem generation pipeline.

    Requires the `X-Admin-Key` header to match the server's ADMIN_API_KEY.
    """
    _verify_admin_key(x_admin_key)

    logger.info("Admin triggered generation pipeline")

    try:
        result = await generate_next_week()
    except Exception as exc:
        logger.exception("Generation pipeline failed")
        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {exc}",
        ) from exc

    return {"status": "success", **result}
