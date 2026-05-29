"""
Public redirect router.
Resolves short-link codes (e.g. /r/pBx3Kq) and redirects to the stored destination.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_session
from app.core.logging import get_logger
from app.domain.models.short_link import ShortLink

logger = get_logger(__name__)

router = APIRouter(tags=["public"])


@router.get("/r/{code}", include_in_schema=False)
async def redirect_short_link(code: str, db: AsyncSession = Depends(get_session)):
    """
    Resolves a short-link code to its destination URL and performs a 302 redirect.
    Returns 404 if the code is not found.
    """
    stmt = select(ShortLink).where(ShortLink.code == code)
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()

    if not link:
        logger.warning("shortlink.not_found", code=code)
        raise HTTPException(status_code=404, detail="Enlace no encontrado")

    logger.info("shortlink.redirect", code=code, destination=link.destination)
    return RedirectResponse(url=link.destination, status_code=302)
