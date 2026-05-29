"""
Authentication router for the Admin Panel.
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import secrets

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-auth"])

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    """Render the login page."""
    # If already logged in, redirect to dashboard
    if request.session.get("authenticated"):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="admin/login.html")

@router.post("/login", response_class=HTMLResponse)
async def process_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process login form."""
    # Constant-time comparison to prevent timing attacks
    is_valid_user = secrets.compare_digest(username, settings.admin_username)
    is_valid_pass = secrets.compare_digest(password, settings.admin_password.get_secret_value())

    if is_valid_user and is_valid_pass:
        request.session["authenticated"] = True
        logger.info("admin.login.success", username=username)
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    
    logger.warning("admin.login.failed", username=username)
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={"error": "Credenciales incorrectas. Intente nuevamente."}
    )

@router.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=302)
