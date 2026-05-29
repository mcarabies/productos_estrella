"""
Dashboard router for authenticated admins.
"""
from fastapi import APIRouter, Request, Form, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sa_delete
import os

from app.core.config import settings
from app.core.database import get_session
from app.core.logging import get_logger
from app.domain.models import Product, ProductImage, Customer, Order
from app.domain.models.short_link import ShortLink
from app.ai.routing import generate_sale_profile
import urllib.parse
import secrets
import string

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Define upload directory for public product photos
UPLOAD_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "uploads")
PRODUCT_IMAGES_DIR = os.path.join(UPLOAD_BASE, "products")
os.makedirs(PRODUCT_IMAGES_DIR, exist_ok=True)

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, db: AsyncSession = Depends(get_session)):
    """Render the main admin dashboard."""
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
        
    # Fetch inventory for the table
    stmt = select(Product).order_by(Product.id.desc())
    result = await db.execute(stmt)
    products = result.scalars().all()

    # Fetch orders (sales)
    stmt_o = select(Order).order_by(Order.created_at.desc()).limit(100)
    result_o = await db.execute(stmt_o)
    orders = result_o.scalars().all()
    
    # Convert UTC timestamps to ART (UTC-3) for display
    from datetime import timezone, timedelta
    art_tz = timezone(timedelta(hours=-3))
    for o in orders:
        if o.created_at:
            if o.created_at.tzinfo is None:
                o.created_at = o.created_at.replace(tzinfo=timezone.utc).astimezone(art_tz)
            else:
                o.created_at = o.created_at.astimezone(art_tz)
    
    # Pass products and orders to template
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "products": products,
        "orders": orders
    })

@router.post("/ingest")
async def process_ingest(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    stock: int = Form(...),
    description_raw: str = Form(""),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_session)
):
    """
    Process form payload including files, use Gemini to generate the structured sale profile, 
    and save the new Product to PostgreSQL.
    """
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="No autenticado")

    logger.info("admin.ingest.start", product_name=name, num_files=len(files))

    try:
        # Prepare files for Gemini (list of (filename, file_bytes, mime_type))
        processed_files = []
        for file in files:
            if file.size and file.size > 0:
                # Read file contents into memory
                file_bytes = await file.read()
                processed_files.append((file.filename, file_bytes, file.content_type))
        
        # 1. Call Gemini 3.1 Pro to extract the structured sale profile
        sale_profile = await generate_sale_profile(name, description_raw, processed_files)

        if not sale_profile:
            logger.error("admin.ingest.ai_failed", product_name=name)
            raise HTTPException(status_code=500, detail="La Inteligencia Artificial no pudo procesar la descripción o archivos del producto. Asegúrate de brindar información válida.")

        # 2. Create and insert the DB Model
        new_product = Product(
            name=name,
            description_raw=description_raw,
            price=price,
            stock=stock,
            is_active=True,
            sale_profile=sale_profile
        )

        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)

        # ── WhatsApp Link Generation ──────────────────────────────────────────
        # We build the full wa.me link, store it in a short_links row,
        # and save ONLY the short URL in product.whatsapp_link.
        # The bot keeps reading product.whatsapp_link as before — zero breakage.
        if settings.bot_phone_number:
            clean_phone = settings.bot_phone_number.replace("+", "").replace(" ", "").replace("-", "")
            base_msg = f"¡Hola! Me interesa este producto.\nEs el {name}.\n\nRef: {new_product.id}"
            encoded_msg = urllib.parse.quote(base_msg)
            full_wa_link = f"https://wa.me/{clean_phone}?text={encoded_msg}"

            # Generate a unique 7-character alphanumeric code
            alphabet = string.ascii_letters + string.digits
            while True:
                code = "".join(secrets.choice(alphabet) for _ in range(7))
                existing = await db.execute(select(ShortLink).where(ShortLink.code == code))
                if existing.scalar_one_or_none() is None:
                    break

            short = ShortLink(code=code, destination=full_wa_link)
            db.add(short)

            # Build the short URL using the public-facing link domain
            short_url = f"https://{settings.link_domain}/r/{code}"
            new_product.whatsapp_link = short_url
            db.add(new_product)
            await db.commit()
            logger.info("admin.ingest.shortlink_created", code=code, short_url=short_url)

        logger.info("admin.ingest.success", product_id=str(new_product.id), product_name=name)
        
        return {
            "status": "success", 
            "message": "Product created and AI profile generated successfully",
            "product_id": str(new_product.id)
        }

    except Exception as e:
        await db.rollback()
        logger.error("admin.ingest.error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ── Product Management Endpoints ──────────────────────────────────────────────

@router.patch("/products/{product_id}/toggle-active")
async def toggle_product_active(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)
    
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    product.is_active = not product.is_active
    await db.commit()
    
    return {"status": "success", "is_active": product.is_active}


@router.patch("/products/{product_id}/stock")
async def update_product_stock(
    request: Request,
    product_id: str,
    stock: int = Form(...),
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)
    
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    product.stock = stock
    await db.commit()
    
    return {"status": "success", "stock": product.stock}


@router.patch("/products/{product_id}/price")
async def update_product_price(
    request: Request,
    product_id: str,
    price: float = Form(...),
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)
    
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    product.price = price
    await db.commit()
    
    return {"status": "success", "price": float(product.price)}


@router.delete("/products/{product_id}")
async def delete_product(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)
    
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    await db.delete(product)
    await db.commit()
    
    return {"status": "success", "message": "Producto eliminado"}


@router.get("/products/{product_id}/profile")
async def get_product_profile(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)
    
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    return {
        "id": product.id,
        "name": product.name,
        "sale_profile": product.sale_profile or {},
        "description_raw": product.description_raw
    }


@router.post("/products/{product_id}/regenerate-profile")
async def regenerate_product_profile(
    request: Request,
    product_id: str,
    context: str = Form(...),
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)
    
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Use the new context and existing data to regenerate
    combined_description = f"DATOS ANTERIORES:\n{product.description_raw}\n\nNUEVAS INSTRUCCIONES/DATOS:\n{context}"
    
    new_profile = await generate_sale_profile(product.name, combined_description)
    
    if new_profile:
        product.sale_profile = new_profile
        await db.commit()
        return {"status": "success", "sale_profile": new_profile}
    
    raise HTTPException(status_code=500, detail="Error al regenerar el perfil con IA.")

@router.patch("/orders/{order_id}/status")
async def update_order_status(
    request: Request,
    order_id: str,
    status: str = Form(...),
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)
        
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
        
    order.status = status
    await db.commit()
    
    return {"status": "success", "new_status": order.status}


# ── Image Gallery Endpoints ───────────────────────────────────────────────────

@router.get("/products/{product_id}/images")
async def get_product_images(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)
    
    stmt = select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.created_at.desc())
    result = await db.execute(stmt)
    images = result.scalars().all()
    
    return [
        {
            "id": str(img.id),
            "url": img.url,
            "is_public": img.is_public
        } for img in images
    ]


@router.post("/products/{product_id}/images")
async def upload_product_image(
    request: Request,
    product_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)

    import uuid
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{product_id}_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(PRODUCT_IMAGES_DIR, unique_filename)
    
    # Save file to static/uploads/products
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # URL to be accessed by the bot and dashboard
    public_url = f"/static/uploads/products/{unique_filename}"
    
    new_image = ProductImage(
        product_id=product_id,
        url=public_url,
        file_path=file_path,
        is_public=True
    )
    
    db.add(new_image)
    await db.commit()
    await db.refresh(new_image)
    
    return {
        "id": str(new_image.id),
        "url": new_image.url,
        "is_public": new_image.is_public
    }


@router.delete("/products/{product_id}/images/{image_id}")
async def delete_product_image(
    request: Request,
    product_id: str,
    image_id: str,
    db: AsyncSession = Depends(get_session)
):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401)
    
    stmt = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    )
    result = await db.execute(stmt)
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    
    # Delete file from disk
    if os.path.exists(image.file_path):
        os.remove(image.file_path)
    
    await db.delete(image)
    await db.commit()
    
    return {"status": "success", "message": "Imagen eliminada"}


# ── Test & Debug Endpoints ────────────────────────────────────────────────────

@router.post("/reset-session")
async def reset_session(
    request: Request,
    phone: str = Form(...),
    db: AsyncSession = Depends(get_session)
):
    """
    Wipes all Redis and Postgres state for a given phone number.
    Use during testing to simulate a brand-new lead without needing a fresh number.
    """
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="No autenticado")
    
    from app.core.session import ChatSessionManager
    from app.domain.models.conversation import Conversation
    
    # Normalize phone: strip spaces, +, dashes
    phone = phone.replace("+", "").replace("-", "").replace(" ", "").strip()
    
    # 1. Wipe Redis history + state
    session_mgr = ChatSessionManager()
    await session_mgr.clear_session(phone)
    logger.info("admin.reset_session.redis_cleared", phone=phone)
    
    # 2. Delete Postgres conversation record
    await db.execute(sa_delete(Conversation).where(Conversation.customer_phone == phone))
    await db.commit()
    logger.info("admin.reset_session.db_cleared", phone=phone)
    
    return JSONResponse({"status": "ok", "message": f"Sesión de {phone} reseteada exitosamente. Puede iniciar una prueba fresh."})

