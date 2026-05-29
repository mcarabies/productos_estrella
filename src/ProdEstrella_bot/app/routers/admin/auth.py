"""
Authentication router for the Admin Panel.
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-auth"])

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Hardcoded credentials as requested
ADMIN_USER = "mcarabies"
ADMIN_PASS = "29232436mjC**"

@router.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    """Render the login page."""
    # If already logged in, redirect to dashboard
    if request.session.get("authenticated"):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return templates.TemplateResponse("admin/login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
async def process_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process login form."""
    if username == ADMIN_USER and password == ADMIN_PASS:
        request.session["authenticated"] = True
        logger.info("admin.login.success", username=username)
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    
    logger.warning("admin.login.failed", username=username)
    return templates.TemplateResponse(
        "admin/login.html", 
        {"request": request, "error": "Credenciales incorrectas. Intente nuevamente."}
    )

@router.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=302)
