"""
Productos Estrella - Motor FastAPI
Sistema de ventas automatizado de Ebooks
"""
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Rutas base ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PRODUCTS_DIR = BASE_DIR / "products"
SHARED_DIR = BASE_DIR / "shared"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Productos Estrella", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Configurar servidor de archivos estáticos con Caché agresivo para PageSpeed
# Note: ST_DIR was not defined in the original code. Assuming it refers to BASE_DIR for static files.
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")

# Middleware para inyectar cabeceras de caché agresivo (1 año) en todos los assets
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    # Cache para /static y para cualquier asset de producto o compartido (.webp, .css, .js, etc.)
    static_extensions = {".webp", ".css", ".js", ".png", ".jpg", ".jpeg", ".woff2", ".svg", ".ico"}
    if path.startswith("/static") or any(path.endswith(ext) for ext in static_extensions):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response

# ── Helpers ───────────────────────────────────────────────────────

def load_tracking_script() -> str:
    """Lee el contenido de shared/scripts_header.html (tracking global)."""
    script_file = SHARED_DIR / "scripts_header.html"
    if script_file.exists():
        return script_file.read_text(encoding="utf-8")
    return "<!-- tracking scripts not configured -->"


def load_product_tracking_script(slug: str) -> str:
    """Lee el contenido de products/{slug}/scripts.html (tracking específico del producto)."""
    product_script_file = PRODUCTS_DIR / slug / "scripts.html"
    if product_script_file.exists():
        try:
            return product_script_file.read_text(encoding="utf-8")
        except Exception as exc:
            logger.error("Error leyendo scripts.html para %s: %s", slug, exc)
    return ""


def inject_tracking(html: str, tracking: str) -> str:
    """Inyecta los scripts de tracking justo antes de </head>."""
    close_head = "</head>"
    if close_head in html:
        return html.replace(close_head, f"{tracking}\n{close_head}", 1)
    # Si no hay </head>, los agrega al inicio del body como fallback
    return tracking + "\n" + html


def get_all_products() -> list[dict]:
    """Escanea /products y retorna la lista de productos parseados."""
    products: list[dict] = []
    if not PRODUCTS_DIR.exists():
        return products

    for folder in sorted(PRODUCTS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        meta_file = folder / "meta.json"
        if not meta_file.exists():
            logger.warning("Carpeta sin meta.json: %s", folder.name)
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            meta["slug"] = folder.name
            # Thumbnail relativo para servir via /static/
            # Thumbnail prioritizando WebP para mejor rendimiento
            thumb_options = [
                folder / "thumbnail.webp",
                folder / "img" / "thumbnail.webp",
                folder / "thumbnail.jpg",
                folder / "img" / "thumbnail.jpg"
            ]
            
            thumb = next((p for p in thumb_options if p.exists()), None)
            
            if thumb:
                # Path relativo para URL estática
                rel_path = f"img/{thumb.name}" if thumb.parent.name == "img" else thumb.name
                meta["thumbnail"] = f"/static/products/{folder.name}/{rel_path}"
            else:
                meta["thumbnail"] = "/static/shared/placeholder.jpg"
            products.append(meta)
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Error leyendo meta.json de %s: %s", folder.name, exc)

    # Ordenar por orden_prioridad (menor = primero)
    products.sort(key=lambda p: p.get("orden_prioridad", 999))
    return products


# ── Rutas ─────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Catálogo de productos — Home."""
    products = get_all_products()
    # Categorías únicas para el filtro
    categories = sorted({p.get("categoria", "General") for p in products})
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "products": products,
            "categories": categories,
        },
    )


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    """Sirve el archivo robots.txt de forma directa para evitar errores de archivo."""
    return """User-agent: *
Allow: /
Sitemap: https://productosestrella.club/sitemap.xml"""


@app.get("/sitemap.xml", response_class=Response)
async def sitemap():
    """Endpoint para sitemap (XML)."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://productosestrella.club/</loc></url>
  <url><loc>https://productosestrella.club/el-arte-del-sueno-profundo/</loc></url>
</urlset>"""
    return Response(content=xml_content, media_type="application/xml")


@app.get("/health")
async def health():
    """Endpoint de health-check para Docker / Traefik."""
    return {"status": "ok"}


@app.get("/{product_slug:path}", response_class=HTMLResponse)
async def landing(product_slug: str, request: Request):
    """
    Landing page dinámica.
    – Si es una carpeta, sirve index.html (inyectando tracking global y de producto)
    – Si es un archivo dentro de una carpeta de producto, lo sirve como estático
    """
    # Redirección de URL antigua con ñ a la nueva sin ñ
    if "sueño" in product_slug:
        new_url = product_slug.replace("sueño", "sueno")
        return RedirectResponse(url=f"/{new_url}", status_code=301)

    parts = product_slug.strip("/").split("/")
    if not parts or not parts[0]:
        return RedirectResponse(url="/")
    
    # El primer elemento siempre es el slug del producto
    slug = parts[0]
    product_dir = PRODUCTS_DIR / slug
    
    if not product_dir.is_dir():
        return RedirectResponse(url="/?error=not_found", status_code=302)

    # Si es exactamente la landing, forzamos la barra final para que las rutas relativas (imágenes) funcionen
    if len(parts) == 1 and not request.url.path.endswith("/"):
        return RedirectResponse(url=f"{request.url.path}/", status_code=301)

    # Si hay más partes, es un recurso (imagen, css, etc.)
    if len(parts) > 1:
        # Prevenir vulnerabilidad de Path Traversal
        try:
            resolved_base = PRODUCTS_DIR.resolve()
            resource_path = (PRODUCTS_DIR / "/".join(parts)).resolve()
            # Validamos que la ruta resuelta esté dentro de PRODUCTS_DIR
            if not resource_path.is_relative_to(resolved_base):
                logger.warning("Intento de Path Traversal bloqueado para: %s", product_slug)
                return RedirectResponse(url="/?error=unauthorized", status_code=302)
        except Exception as exc:
            logger.error("Error validando ruta del recurso para %s: %s", product_slug, exc)
            return RedirectResponse(url="/?error=not_found", status_code=302)

        if resource_path.exists() and resource_path.is_file():
            return FileResponse(resource_path)
        return RedirectResponse(url=f"/{slug}/")

    # Cargar landing principal (index.html)
    landing_file = product_dir / "index.html"
    if not landing_file.exists():
        logger.warning("Landing index.html faltante para: %s", slug)
        return RedirectResponse(url="/?error=no_landing", status_code=302)

    raw_html = landing_file.read_text(encoding="utf-8")
    
    # Cargar y combinar tracking global y específico de producto
    global_tracking = load_tracking_script()
    product_tracking = load_product_tracking_script(slug)
    
    combined_tracking = global_tracking
    if product_tracking:
        combined_tracking += "\n" + product_tracking
        
    final_html = inject_tracking(raw_html, combined_tracking)

    return HTMLResponse(content=final_html, status_code=200)
