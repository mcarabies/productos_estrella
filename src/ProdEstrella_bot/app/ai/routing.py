"""
AI Routing — Three-Stage Model Router.
Integrates google-genai SDK for product ingestion, negotiation, and closing.
"""
from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger
from app.core.session import ChatSessionManager
from app.domain.models.product import Product, ProductImage
from app.domain.models.customer import Customer
from app.domain.models.order import Order, OrderStatus

logger = get_logger(__name__)

# Initialize the Gemini GenAI client using the API key from settings
# We'll use synchronous client inside our async function using standard asyncio patterns if needed,
# or the async client if available. google-genai provides `genai.Client`.
client = genai.Client(api_key=settings.google_api_key.get_secret_value())

# ── Prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_NEGOTIACION = """Eres *Estrella*, el vendedor principal y experto de Productos Estrella. Vendemos de todo: tecnología, bazar, artículos para el hogar, útiles, y muchos productos más.
Tu objetivo es ayudar al cliente, buscar los productos en nuestro inventario, y llevarlo amigablemente hacia el cierre de la compra.

REGLAS ESTRICTAS:
1. NUNCA inventes productos, stocks ni precios. Si el cliente pregunta por algo, USA OBLIGATORIAMENTE tu herramienta `consultar_inventario`. MÁXIMO 1 o 2 búsquedas por mensaje. No entres en bucle si no encuentres nada.
2. Habla en español de Argentina (voseo, amigable pero profesional, usa emojis moderadamente).
3. CONVERSACIÓN INICIAL (CRÍTICO): En el primer contacto o los primeros dos mensajes, NO intentes cerrar la venta directamente ni preguntes por cantidades. Inicia una breve charla sobre el producto para generar confianza, destacar sus beneficios o utilidades, y ofrécele enviarle fotos si desea verlo mejor. Tu prioridad al principio es evacuar dudas y enamorar con el producto.
4. CIERRE DE VENTA GRADUAL: Sólo cuando hayan pasado 2 o 3 mensajes intercambiados (o si el cliente ya indica una intención de compra directa y apurada), pregúntale: "¿Cuántas unidades vas a querer?". JAMÁS asumas que es 1 unidad por defecto. Cuando te confirme la cantidad, invoca la herramienta `agregar_al_carrito`. Si ves oportuno, ofrécele algo complementario que tengamos en inventario, pero hazlo con naturalidad.
5. PROHIBIDO hablar de medios de pago en esta etapa, NUNCA menciones transferencias bancarias ni retiros en el local. Solo hacemos ENVÍOS a domicilio.
6. Si el cliente tiene una objeción, usa el "objection_tree" del perfil del producto para rebatirla.
7. CRÍTICO: Cuando el cliente diga "No", "Solo eso", "Quiero pagar" o indique claramente que no agregará más productos, ESTÁS OBLIGADO a invocar la herramienta `proceder_al_pago` INMEDIATAMENTE. ¡Peligro!: NO respondas con un mensaje de despedida ni des la venta por "cerrada" en texto. Tu Única y exclusiva acción válida es ejecutar `proceder_al_pago` para que el sistema recolecte los datos.
8. 🛑 REGLA ABSOLUTA POST-VENTA (AGRADECIMIENTOS): Si el cliente te agradece o dice "gracias" o cualquier mensaje positivo de despedida, Y en el historial reciente ya EXISTE un mensaje del sistema que menciona un link de pago o un N° de operación o '¡Tu pago fue aprobado!', entonces DEBES responder ÚNICAMENTE con: «¡Gracias a vos por elegir Productos Estrella! 🌟 Cualquier novedad sobre el envío te avisamos por este mismo medio.». NO llames `agregar_al_carrito` ni `proceder_al_pago` ni `consultar_inventario`. CERO acciones de venta. PUNTO FINAL.
9. VERIFICACIÓN PREVIA AL PAGO: Antes de llamar `proceder_al_pago`, si el carrito tiene items, muestra al cliente el resumen del carrito para que lo confirme. Ej: "¡Genial! Voy a gestionar el pago para: 1x Regla de 30 cm ($1900). ¿Confirmás que ese es tu pedido?". Solo llama `proceder_al_pago` cuando el cliente diga «salvo confirmar» o afirme el pedido.
"""


SYSTEM_PROMPT_CIERRE = """Eres el Asistente de Cierre de Ventas de Productos Estrella. Hablás directamente con el cliente por WhatsApp (voseo argentino, amigable y profesional).

Tu objetivo principal es recolectar los datos de envío y generar el link de pago. PERO si el cliente quiere modificar su pedido (cambiar cantidades, quitar o agregar productos), atendelo con total flexibilidad como un vendedor de salón.

CARRITO:
- Podés usar `modificar_carrito` para cambiar cantidades o eliminar productos.
- Podés usar `agregar_al_carrito` para sumar productos nuevos.
- Podés usar `consultar_inventario` si el cliente pregunta por otro producto.
- Después de cada cambio, mostralo al cliente y preguntá si quiere seguir modificando o proceder al pago.

LISTA DE VERIFICACIÓN para el pago:
- [ ] Nombre Completo
- [ ] DNI (sólo números, mínimo 7 dígitos)
- [ ] Email (con @ y dominio)
- [ ] Dirección de envío (Calle, Número, Ciudad, Provincia)
- [ ] Código Postal (sólo números)

PASOS:
1. Si tenés datos del cliente del CRM/historial, MOSTRÁSELOS para que confirme: «Tengo estos datos tuyos: [datos]. ¿Esthey están bien o querés cambiar algo?»
2. Pedí SOLO los datos que faltan. Nunca pidas lo que ya tenés.
3. El DNI debe ser solo números (7+ dígitos). Si no es válido, volvé a pedirlo.
4. Cuando tengas los 5 datos confirmados, ejecutá `generar_link_de_pago` INMEDIATAMENTE.

REGLAS:
- Hablá DIRECTO al cliente, NUNCA en tercera persona ('pedíselo al cliente' es INCORRECTO, lo correcto es '¿Me pasás tu DNI?').
- NUNCA menciones transferencia bancaria ni retiro en local. Único método: link de MercadoPago.
- Si algo falta, pedílo amablemente al cliente, NUNCA digas que hay un 'error técnico'.
"""



async def consultar_inventario(nombre_o_categoria: str) -> str:
    """
    Busca productos en la base de datos (inventario) mediante un término de búsqueda. 
    Retorna el nombre, descripción, stock, precio en ARS y perfil de venta de los productos si se encuentran, 
    o un mensaje indicando que no hay resultados.

    Args:
        nombre_o_categoria: El producto que el cliente está buscando o preguntando (ej. "sillón", "auriculares", "JBL").
    """
    from sqlalchemy.future import select
    from app.core.database import AsyncSessionLocal

    logger.info("ai.tool.consultar_inventario", query=nombre_o_categoria)
    
    async with AsyncSessionLocal() as db:
        # Check for generic queries
        generic_terms = ["", "todo", "stock", "productos", "catálogo", "catalogo", "lista"]
        is_generic = nombre_o_categoria.lower().strip() in generic_terms
        
        # We replace some common accents for a simple manual unaccent
        search_term = nombre_o_categoria.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")

        if is_generic:
            stmt = select(Product).where(Product.is_active == True).limit(10)
        else:
            from sqlalchemy import or_, and_
            
            # Split into individual words
            words = search_term.split()
            
            # Create a list of ILIKE conditions for each word
            conditions = []
            for word in words:
                word = word.strip()
                if not word:
                    continue
                # Match if the word is found anywhere in the name or description
                conditions.append(or_(
                    Product.name.ilike(f"%{word}%"),
                    Product.description_raw.ilike(f"%{word}%")
                ))
            
            # If no valid words were found, default to generic search
            if not conditions:
                 stmt = select(Product).where(Product.is_active == True).limit(10)
            else:
                 # It must match at least ONE of the valid words (or_)
                 # We limit to 5 results to avoid context overflow for the AI
                 stmt = select(Product).where(
                     Product.is_active == True,
                     or_(*conditions)
                 ).limit(5)
            
        result = await db.execute(stmt)
        products = result.scalars().all()
        
        if not products:
            if is_generic:
                 return "El inventario está vacío en este momento."
            return f"No se encontró ningún producto activo que coincida con la búsqueda '{nombre_o_categoria}'. Pídele al cliente que intente con otros términos."
            
        context = "RESULTADOS DEL INVENTARIO (Usa esta info para responder al cliente y MENCIONA ESTOS PRODUCTOS DISPONIBLES):\n\n"
        for p in products:
            context += f"- Nombre: {p.name}\n"
            context += f"  product_id: {p.id}\n"
            context += f"  Stock actual: {p.stock} unidades\n"
            context += f"  Precio Base: ${p.price}\n"
            if p.sale_profile:
                context += f"  Perfil de venta activo: {json.dumps(p.sale_profile, ensure_ascii=False)}\n\n"
            else:
                context += "\n\n"
            context += "\n"
        return context


async def route_message(
    phone: str,
    message_text: str,
    conversation_stage: str,
    *,
    sale_profile: dict | None = None,
) -> str:
    """
    Route a customer message to the appropriate Gemini 3.x model.
    """
    logger.info(
        "ai.route_message.start",
        phone=phone,
        stage=conversation_stage,
    )

    session_mgr = ChatSessionManager()
    
    # 1. Fetch previous history from Redis
    raw_history = await session_mgr.get_chat_history(phone, limit=20)
    
    # AUTO-CLEAN: If this is the very first message of a fresh conversation,
    # nuke any leftover cart from a previous session to prevent ghost accumulation.
    if len(raw_history) == 0:
        r_autoclear = await session_mgr._get_redis()
        cart_key_autoclear = session_mgr._get_cart_key(phone)
        state_key_autoclear = session_mgr._get_state_key(phone)
        await r_autoclear.delete(cart_key_autoclear)
        # Also reset any payment_completed flag from previous session
        prev_state = await session_mgr.get_state(phone)
        if prev_state.get("payment_completed"):
            await r_autoclear.set(state_key_autoclear, json.dumps({"stage": "negotiation"}), ex=settings.redis_session_ttl)
        logger.info("ai.route_message.autoclear_cart", phone=phone)
    
    # 2. Add current user message to Redis
    await session_mgr.add_message(phone, role="user", content=message_text)

    # ── HARD INTERCEPT: Post-payment thank-you ──────────────────────────────
    # If a payment was already completed in this session, DO NOT call Gemini at all.
    # Just return a thank-you message directly. This prevents the AI from re-entering
    # the closing flow when the client says "gracias" after paying.
    state_check = await session_mgr.get_state(phone)
    if state_check.get("payment_completed"):
        thank_you = "¡Gracias a vos por elegir *Productos Estrella*! 🌟 Ya estamos preparando tu envío. Cualquier novedad te avisamos por este mismo medio. ¡Que tengas un excelente día! 😊"
        await session_mgr.add_message(phone, role="model", content=thank_you)
        logger.info("ai.route_message.post_payment_intercept", phone=phone)
        return thank_you

    # Convert Redis history format to Gemini SDK format
    contents = []
    for msg in raw_history:
        # Convert "user" -> "user", "model" -> "model" for Gemini
        role = msg.get("role", "user")
        if role not in ["user", "model"]:
            role = "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))]))
    
    # Add the current message
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message_text)]))

    async def send_product_photos(product_id: str) -> str:
        """
        Envía las fotos públicas del producto especificado directamente al chat del cliente.
        Usa esto SOLAMENTE cuando el cliente pida explícitamente ver fotos del producto que le interesa.
        DEBES invocarla pasándole el ID exacto del producto devuelto por el inventario o tu contexto inicial.
        """
        from sqlalchemy.future import select
        from app.core.database import AsyncSessionLocal
        from app.messaging.factory import get_whatsapp_provider

        logger.info("ai.tool.send_product_photos", product_id=product_id, phone=phone)

        async with AsyncSessionLocal() as db:
            stmt = select(ProductImage).where(
                ProductImage.product_id == product_id,
                ProductImage.is_public == True
            )
            result = await db.execute(stmt)
            images = result.scalars().all()

        if not images:
            return "Lo siento, acabo de revisar y no tenemos fotos públicas disponibles para este producto."
        
        adapter = get_whatsapp_provider()
        
        # We need an absolute URL for Evolution API/Meta if possible, or just send the relative path if Evolution serves it.
        # But generally we construct it via app_domain. We use dash.productosestrella.club here for production.
        domain = "dash.productosestrella.club" if settings.app_env == "production" else "localhost"
        
        try:
            for img in images:
                media_url = f"https://{domain}{img.url}"
                # Sending via adapter
                await adapter.send_media(phone, media_url, media_type="image")
            return "¡Listo! Le acabo de enviar las fotos a tu chat. Pregúntale al cliente qué le parecieron y ofrécele de nuevo el cierre."
        except Exception as e:
            logger.error("ai.tool.send_product_photos_failed", error=str(e))
            return "Hubo un error enviando las fotos al sistema, pídele disculpas e intenta cerrar la venta sin las fotos."

    async def agregar_al_carrito(product_id: str, cantidad: int = 1) -> str:
        """
        Establece la cantidad de un producto en el carrito de compras virtual del cliente.
        Llama a esta herramienta CADA VEZ que el cliente confirme que quiere llevar un producto.
        Si el producto ya está en el carrito, la cantidad se REEMPLAZA (no se suma).
        """
        try:
            cantidad = int(cantidad)
        except (ValueError, TypeError):
            cantidad = 1
        if cantidad < 1:
            cantidad = 1
            
        product_id = str(product_id)

        from sqlalchemy.future import select
        from app.core.database import AsyncSessionLocal

        logger.info("ai.tool.agregar_al_carrito", phone=phone, product_id=product_id, cantidad=cantidad)
        
        # Get Redis client and keys upfront
        r_client = await session_mgr._get_redis()
        cart_key = session_mgr._get_cart_key(phone)
        state_key = session_mgr._get_state_key(phone)
        
        # If previous payment was completed, wipe the cart for a fresh start
        state_guard = await session_mgr.get_state(phone)
        if state_guard.get("payment_completed"):
            logger.info("ai.tool.agregar_al_carrito.new_purchase_after_payment", phone=phone)
            await r_client.delete(cart_key)
            await r_client.set(state_key, json.dumps({"stage": "negotiation"}), ex=settings.redis_session_ttl)
        
        async with AsyncSessionLocal() as db:
            stmt = select(Product).where(Product.id == product_id)
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()
            
            if not product:
                return "Error: no encontré el producto en la base de datos."
            
            if not product.is_active:
                return f"Lo siento, el producto {product.name} no está disponible actualmente."
            
            # Stock check BEFORE touching the cart
            if product.stock < cantidad:
                return f"Lo siento, solo tenemos {product.stock} unidades de {product.name} en stock."
            
            # Read current cart
            raw_cart = await r_client.get(cart_key)
            cart = json.loads(raw_cart) if raw_cart else []
            
            # ── SET SEMANTICS (NOT ADD) ──
            # If the product is already in the cart, REPLACE the quantity.
            # This prevents doubling when Gemini calls this tool multiple times
            # in its internal iteration loop.
            product_id_str = str(product.id)
            existing_item = next((item for item in cart if item["product_id"] == product_id_str), None)
            
            if existing_item:
                existing_item["quantity"] = cantidad  # SET, not +=
            else:
                cart.append({
                    "product_id": product_id_str,
                    "name": product.name,
                    "price": float(product.price),
                    "quantity": cantidad
                })
            
            # Save back to Redis
            await r_client.set(cart_key, json.dumps(cart), ex=settings.redis_session_ttl)
            
            # Build exact cart summary for the AI to relay to the customer
            resumen = ", ".join([f"{i['quantity']}x {i['name']} (${i['price']:,.0f} c/u)" for i in cart])
            total = sum(i['price'] * i['quantity'] for i in cart)
            return f"✅ Carrito actualizado. Contenido actual del carrito: {resumen}. Total: ${total:,.2f}. Comunicale al cliente este resumen EXACTO, sin cambiar las cantidades, y preguntale si quiere sumar algo más o pasar al pago."

    async def modificar_carrito(product_id: str, nueva_cantidad: int) -> str:
        """
        Modifica la cantidad de un producto que YA está en el carrito, o lo elimina.
        Si nueva_cantidad es 0, el producto se elimina del carrito.
        Si nueva_cantidad > 0, se actualiza la cantidad a ese número exacto.
        Usalo cuando el cliente quiera cambiar cantidades o quitar un producto.
        """
        try:
            nueva_cantidad = int(nueva_cantidad)
        except (ValueError, TypeError):
            return "Error: cantidad inválida."
        
        product_id = str(product_id)
        r_client = await session_mgr._get_redis()
        cart_key = session_mgr._get_cart_key(phone)
        
        raw_cart = await r_client.get(cart_key)
        cart = json.loads(raw_cart) if raw_cart else []
        
        if not cart:
            return "El carrito está vacío, no hay nada que modificar."
        
        existing_item = next((item for item in cart if item["product_id"] == product_id), None)
        
        if not existing_item:
            return f"No encontré ese producto en el carrito. Productos en el carrito: {', '.join(i['name'] for i in cart)}."
        
        product_name = existing_item["name"]
        
        if nueva_cantidad <= 0:
            cart = [item for item in cart if item["product_id"] != product_id]
            await r_client.set(cart_key, json.dumps(cart), ex=settings.redis_session_ttl)
            
            if not cart:
                return f"✅ Se eliminó {product_name} del carrito. El carrito quedó vacío. Preguntale al cliente qué quiere hacer."
            else:
                resumen = ", ".join([f"{i['quantity']}x {i['name']} (${i['price']:,.0f} c/u)" for i in cart])
                total = sum(i['price'] * i['quantity'] for i in cart)
                return f"✅ Se eliminó {product_name}. Carrito actualizado: {resumen}. Total: ${total:,.2f}. Comunicale al cliente y preguntá si quiere continuar con el pago."
        else:
            from sqlalchemy.future import select
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                from app.domain.models.product import Product
                stmt = select(Product).where(Product.id == product_id)
                result = await db.execute(stmt)
                product = result.scalar_one_or_none()
                if product and product.stock < nueva_cantidad:
                    return f"Solo tenemos {product.stock} unidades de {product_name} en stock."
            
            existing_item["quantity"] = nueva_cantidad
            await r_client.set(cart_key, json.dumps(cart), ex=settings.redis_session_ttl)
            
            resumen = ", ".join([f"{i['quantity']}x {i['name']} (${i['price']:,.0f} c/u)" for i in cart])
            total = sum(i['price'] * i['quantity'] for i in cart)
            return f"✅ Carrito actualizado: {resumen}. Total: ${total:,.2f}. Comunicale al cliente y preguntá si quiere continuar con el pago o hacer otro cambio."

    async def proceder_al_pago() -> str:
        """
        Obligatorio. Llama a esta función SOLO cuando el cliente diga que ya no quiere agregar NADA MÁS y desea pagar el total de su pedido.
        Esta acción bloquea la charla y lo pasa a la etapa de cierre.
        """
        from app.core.database import AsyncSessionLocal
        from app.domain.models.conversation import Conversation, ConversationStage
        from sqlalchemy.future import select

        logger.info("ai.tool.proceder_al_pago.start", phone=phone)

        # Ensure they have something in the cart — read from dedicated cart_key
        r_client = await session_mgr._get_redis()
        cart_key = session_mgr._get_cart_key(phone)
        raw_cart = await r_client.get(cart_key)
        cart = json.loads(raw_cart) if raw_cart else []
        
        if not cart:
             return "ERROR: El carrito está vacío. Si el cliente ya pagó o se generó su link, simplemente contesta agradeciéndole la compra o diciéndole que su envío está en preparación (NO reinicies el proceso). Si no compró nada, pregúntale qué busca."

        # Transition stage
        await session_mgr.update_state(phone, {"stage": "closing"})
        
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(Conversation).where(Conversation.customer_phone == phone)
                result = await db.execute(stmt)
                conv = result.scalar_one_or_none()
                if conv:
                    conv.stage = ConversationStage.closing
                    await db.commit()
                else:
                    logger.warning("ai.tool.proceder_al_pago.conv_not_found", phone=phone)
        except Exception as e:
            logger.error("ai.tool.proceder_al_pago.db_error", phone=phone, error=str(e))

        # This will be intercepted and sent DIRECTLY to the closing AI as context
        items_str = ", ".join([f"{i['quantity']}x {i['name']}" for i in cart])
        total = sum([i['price'] * i['quantity'] for i in cart])
        
        # Look up existing customer data in the DB for pre-filling
        known_data_section = ""
        try:
            from app.domain.models import Customer
            from sqlalchemy.future import select as sa_select
            async with AsyncSessionLocal() as db2:
                stmt_cust = sa_select(Customer).where(Customer.phone == phone)
                res_cust = await db2.execute(stmt_cust)
                existing_customer = res_cust.scalar_one_or_none()
                if existing_customer:
                    shipping = existing_customer.shipping_data or {}
                    known_data_section = (
                        f"\n\n📋 *Datos que tenemos de vos en nuestro sistema:*\n"
                        f"• Nombre: {existing_customer.name}\n"
                        f"• DNI: {existing_customer.document_id}\n"
                        f"• Email: {existing_customer.email}\n"
                        f"• Dirección: {shipping.get('address', 'No registrada')}\n\n"
                        f"¿Estos datos son correctos para este pedido? ¿O querés usar una dirección diferente?"
                    )
        except Exception:
            pass
        
        if known_data_section:
            return f"¡Excelente elección! Tu pedido:\n🛒 *{items_str}*\n💰 *Total: ${total:,.2f}*{known_data_section}\n\nSi todo está bien, confirmame y generamos el link. Si querés cambiar algún dato, avisame cuál."
        else:
            return f"¡Excelente elección! Acabo de preparar tu pedido:\n🛒 *{items_str}*\n💰 *Total: ${total:,.2f}*\n\nPara enviarte el link de pago seguro y armar tu paquete, necesito estos datos:\n1. Nombre Completo\n2. DNI\n3. Email\n4. Dirección de envío local (Calle, número, localidad, provincia)\n5. Código Postal (esencial para el despacho).\n\n¡Pásamelos por acá y lo cerramos!"

    async def generar_link_de_pago(
        name: str,
        dni: str,
        email: str,
        full_shipping_address: str
    ) -> str:
        """
        Obligatorio. Usa esto para generar el link de pago de MercadoPago por el total del carrito.
        """
        import asyncio
        from app.core.database import AsyncSessionLocal
        from app.domain.models import Customer, Order
        from app.domain.models.order import OrderStatus
        from app.payments.mercadopago import create_preference
        from sqlalchemy.future import select

        logger.info("ai.tool.generar_link_de_pago.start", dni=dni, email=email)
        
        # Read cart from dedicated cart_key
        r_client2 = await session_mgr._get_redis()
        cart_key2 = session_mgr._get_cart_key(phone)
        raw_cart2 = await r_client2.get(cart_key2)
        cart = json.loads(raw_cart2) if raw_cart2 else []
        if not cart:
            return "El carrito está vacío. ¿Qué producto quería el cliente?"

        # Validaciones de seguridad pre-MercadoPago
        # IMPORTANT: These messages are sent DIRECTLY to the customer (intercepted),
        # so they must sound like a seller talking to a buyer, NOT internal instructions.
        dni_clean = str(dni).strip().replace(" ", "").replace(".", "")
        if not dni_clean or len(dni_clean) < 7 or not dni_clean.isdigit():
            return "Para poder generarte el link de pago necesito tu número de DNI (solo números, sin puntos). ¿Me lo pasás? 🙏"
        if "@" not in str(email) or "." not in str(email):
            return "Me falta tu email para enviarte el comprobante de pago. ¿Me lo pasás? 📧"
        if not name or len(str(name).strip().split()) < 2:
            return "Necesito tu nombre y apellido completo para la facturación. ¿Me lo confirmás? 📝"

        async with AsyncSessionLocal() as db:
            # 1. UPSERT Customer
            stmt_c = select(Customer).where(Customer.document_id == dni)
            res_c = await db.execute(stmt_c)
            customer = res_c.scalar_one_or_none()

            shipping_dict = {
                "address": full_shipping_address,
            }

            if not customer:
                logger.info("ai.tool.save_payment.creating_customer", dni=dni)
                customer = Customer(
                    document_id=dni,
                    name=name,
                    phone=phone,
                    email=email,
                    shipping_data=shipping_dict
                )
                db.add(customer)
                await db.flush()  # CRITICAL: flush so the FK constraint is satisfied before Order creation
            else:
                logger.info("ai.tool.save_payment.updating_customer", dni=dni)
                customer.name = name
                customer.email = email
                customer.shipping_data = shipping_dict
                customer.phone = phone

            # 2. Total calculation
            total_amount = sum(item["price"] * item["quantity"] for item in cart)

            # 3. Create Order
            # We map the cart to the new items JSONB column
            order = Order(
                customer_dni=dni,
                customer_phone=phone,
                product_id=None, # Explicitly null since we use items now
                items=cart,
                total_amount=float(total_amount),
                status=OrderStatus.pending_payment
            )
            db.add(order)
            await db.flush()  # Get order.id before MP call
            logger.info("ai.tool.save_payment.order_created", order_id=str(order.id))

            # 4. Build enriched MP items (Quality Checklist: id, title, description, category_id)
            mp_items = []
            for item in cart:
                qty = int(item.get("quantity", 1))
                price = float(item.get("price", 0))
                if qty <= 0:
                    continue
                mp_items.append({
                    "product_id": str(item.get("product_id", "")),  # passed as items[*].id
                    "title": str(item["name"]),
                    "description": str(item["name"]),  # Best we have without DB round-trip
                    "unit_price": price,
                    "quantity": qty,
                    "currency_id": "ARS",
                })

            # 5. Create MP Preference with full payer data (Quality Checklist compliant)
            try:
                logger.info("ai.tool.save_payment.calling_mp", order_id=str(order.id))
                pref = await create_preference(
                    items=mp_items,
                    payer_email=email,
                    external_reference=str(order.id),
                    payer_name=name,
                    payer_dni=dni,
                    payer_phone=phone,
                    shipping_address=full_shipping_address,
                )
                order.mp_preference_id = pref["id"]
                await db.commit()
                logger.info("ai.tool.save_payment.success", order_id=str(order.id), init_point=pref.get("init_point", ""))
                
                # ── HARD CLEAR — nuke cart_key AND reset state with payment_completed flag ──
                state_key = session_mgr._get_state_key(phone)
                cart_key_final = session_mgr._get_cart_key(phone)
                r_final = await session_mgr._get_redis()
                # Set payment_completed=True so agregar_al_carrito blocks post-payment additions
                await r_final.set(state_key, json.dumps({"stage": "negotiation", "payment_completed": True}), ex=settings.redis_session_ttl)
                await r_final.delete(cart_key_final)
                
                # Intercepted output — send directly to customer without re-running Gemini
                return f"¡Listo! Pude generar el link para abonar tu orden ({order.id}).\n\n👉 *Pagá de forma segura en Mercado Pago aquí*: {pref.get('init_point', '')}\n\nUna vez que se acredite, prepararemos todo para enviar a {full_shipping_address}."
            except Exception as mp_err:
                await db.rollback()
                logger.error("ai.tool.mp_failed", error=str(mp_err), order_id=str(order.id))
                return "Hubo un problema técnico generando el link de pago con MercadoPago. Por favor, intenta de nuevo en unos momentos."


    # Determine Model and System Instructions based on Stage
    tools = None
    if conversation_stage == "negotiation":
        model_name = settings.ai_stage2_model
        sys_instruct = SYSTEM_PROMPT_NEGOTIACION
        
        # ── Context Injection ────────────────────────────────────────────────
        state_data = await session_mgr.get_state(phone)
        context_product_id = state_data.get("context_product_id")
        
        if context_product_id:
            from sqlalchemy.future import select
            from app.core.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                stmt = select(Product).where(Product.id == context_product_id)
                result = await db.execute(stmt)
                context_product = result.scalar_one_or_none()
                
                if context_product:
                    sys_instruct += f"\n\nATENCIÓN: Cuentas con un PRODUCTO CONTEXTUAL. Esto significa que el cliente hizo clic en un link específico desde redes sociales pidiendo el producto ID: {context_product.id}\n"
                    sys_instruct += f"Detalles: {context_product.name}. Precio: ${context_product.price}. Status Activo: {context_product.is_active}.\n"
                    if context_product.sale_profile:
                        sys_instruct += f"Perfil de venta inicial para usar AHORA: {json.dumps(context_product.sale_profile, ensure_ascii=False)}\n"
                    
                    if not context_product.is_active:
                        sys_instruct += "\nEL PRODUCTO ESTÁ INACTIVO O SIN STOCK. DISCULPATE Y OBRÍGALE INVENTARIAR ALGO SIMILAR."
                    
        tools = [consultar_inventario, send_product_photos, agregar_al_carrito, modificar_carrito, proceder_al_pago]
    
    elif conversation_stage == "closing":
        model_name = settings.ai_stage3_model
        sys_instruct = SYSTEM_PROMPT_CIERRE
        
        # ── Product Context Injection (read from dedicated cart_key) ──────────
        r_closing = await session_mgr._get_redis()
        cart_key_closing = session_mgr._get_cart_key(phone)
        raw_cart_closing = await r_closing.get(cart_key_closing)
        cart = json.loads(raw_cart_closing) if raw_cart_closing else []
        
        if cart:
            sys_instruct += f"\n\n=== CARRITO ACTUAL (MODIFICABLE si el cliente lo pide) ===\n"
            for item in cart:
                sys_instruct += f"- {item['quantity']}x {item['name']} (ID: {item['product_id']}, Precio Unitario: ${item['price']})\n"
            sys_instruct += f"=== Si el cliente quiere cambiar algo, usá modificar_carrito o agregar_al_carrito ==="
        else:
            sys_instruct += "\n\nATENCIÓN: EL CARRITO ESTÁ VACÍO. Esto es anómalo, pregunta al cliente qué quería comprar."

        # ── CRM Context Injection ──────────────────────────────────────────
        from sqlalchemy.future import select
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            # Check if customer exists by phone
            stmt_c = select(Customer).where(Customer.phone == phone)
            res_c = await db.execute(stmt_c)
            customer_entity = res_c.scalar_one_or_none()
            
            if customer_entity:
                sys_instruct += "\n\nDATOS DEL CLIENTE ENCONTRADOS (CRM):"
                sys_instruct += f"\nNombre: {customer_entity.name}\nDNI: {customer_entity.document_id}\nEmail: {customer_entity.email}"
                if customer_entity.shipping_data:
                    ship = customer_entity.shipping_data
                    sys_instruct += f"\nÚltimo Envío: {ship.get('address')}, {ship.get('city')}, {ship.get('province')} (CP: {ship.get('zip_code')})"
                
                # Also inject last 3 orders
                stmt_o = select(Order).where(Order.customer_dni == customer_entity.document_id).order_by(Order.created_at.desc()).limit(3)
                res_o = await db.execute(stmt_o)
                orders = res_o.scalars().all()
                if orders:
                    sys_instruct += "\nHISTORIAL DE COMPRAS RECIENTES:"
                    for o in orders:
                        sys_instruct += f"\n- Orden {o.id}: Status {o.status}, Monto: {o.total_amount} {o.currency}"
        
        tools = [generar_link_de_pago, modificar_carrito, agregar_al_carrito, consultar_inventario]
    
    elif conversation_stage == "intake":
        model_name = settings.ai_stage1_model
        sys_instruct = "Eres el asistente de ingestión de Productos Estrella. Tu trabajo es analizar el texto/imagen provisto y devolver un JSON estructurado de la información del producto."
    else:
        model_name = settings.ai_stage2_model
        sys_instruct = "Eres un asistente amigable."

    # 3. Call Gemini API
    try:
        # We handle function calling MANUALLY in our loop to have control over interceptions.
        # We pass tools here so the model knows they exist. We completely disable AFC internal loops.
        config = types.GenerateContentConfig(
            system_instruction=sys_instruct,
            temperature=0.2, # Lower temperature for deterministic tool usage
            tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )

        reply_text = None
        max_calls = 8  # Needs room for: inventory search + add to cart + upsell search + text response
        
        # We wrap generation in a retry block because 3.1 models are prone to 503 spikes
        async def call_gemini_with_retry(m_name, m_contents, m_config, max_retries=2):
            import asyncio
            for attempt in range(max_retries + 1):
                try:
                    return await client.aio.models.generate_content(
                        model=m_name,
                        contents=m_contents,
                        config=m_config,
                    )
                except Exception as e_gen:
                    if "503" in str(e_gen) and attempt < max_retries:
                        logger.warning("ai.gemini_retry", attempt=attempt, error=str(e_gen))
                        await asyncio.sleep(1) # Wait a bit
                        continue
                    raise e_gen

        for iteration in range(max_calls):
            # IMPORTANT: We use the manual generation to avoid the SDK's internal AFC loop
            # which adds significant latency and bypasses our interceptors.
            response = await call_gemini_with_retry(model_name, contents, config)
            
            if response.function_calls:
                # Append model's response part containing function calls
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)
                
                tool_responses = []
                for fc in response.function_calls:
                    func_name = fc.name
                    func_args = fc.args
                    logger.info("ai.tool.call_requested", function=func_name, args=dict(fc.args), iteration=iteration)
                    
                    if tools:
                        func = next((f for f in tools if f.__name__ == func_name), None)
                        if func:
                            try:
                                result = await func(**func_args)
                            except Exception as e:
                                logger.error("ai.tool.execution_error", function=func_name, error=str(e))
                                result = f"Error executing tool: {str(e)}"
                            
                            tool_part = types.Part.from_function_response(
                                name=func_name,
                                response={"result": result}
                            )
                            tool_responses.append(tool_part)
                
                if tool_responses:
                    contents.append(types.Content(role="user", parts=tool_responses))
                    
                    # ── INTERCEPT CRITICAL TOOLS TO PREVENT HALLUCINATIONS ──
                    # If the AI called an action that transitions the stage or finishes a transaction,
                    # we do NOT feed it back to Gemini to avoid re-writing/hallucinating. 
                    # We return the raw string directly to the user.
                    for fc in response.function_calls:
                        if fc.name in ("proceder_al_pago", "generar_link_de_pago"):
                            # Find the tool result for this function call
                            for part in tool_responses:
                                try:
                                    resp_name = part.function_response.name
                                except AttributeError:
                                    continue
                                if resp_name == fc.name:
                                    result_val = part.function_response.response.get("result", "")
                                    logger.info("ai.tool.intercepted", function=fc.name)
                                    return result_val
                                    
                    continue # Loop back to get the final text response
                
                # If we got function_calls but no matching tools found, break to avoid infinite loop
                reply_text = "Disculpa, hubo un problema procesando las opciones internamente."
                break
            
            # No function call — plain text response
            text = getattr(response, 'text', None)
            if not text and response.candidates:
                # Grab text from parts manually if .text shortcut fails
                parts = response.candidates[0].content.parts if response.candidates[0].content else []
                text = " ".join(p.text for p in parts if hasattr(p, 'text') and p.text)
            logger.info("ai.route_message.text_response", stage=conversation_stage, iteration=iteration, has_text=bool(text))
            reply_text = text
            break
            
        if not reply_text:
            # The model used ALL iterations calling tools (upselling) and never produced text.
            # Force ONE FINAL call WITHOUT tools so it MUST respond with text.
            logger.warning("ai.route_message.forcing_text_response", phone=phone, iterations=max_calls)
            try:
                forced_config = types.GenerateContentConfig(
                    system_instruction=sys_instruct,
                    temperature=0.3,
                    # NO tools → model is FORCED to produce text
                )
                forced_response = await call_gemini_with_retry(model_name, contents, forced_config)
                forced_text = getattr(forced_response, 'text', None)
                if not forced_text and forced_response.candidates:
                    parts = forced_response.candidates[0].content.parts if forced_response.candidates[0].content else []
                    forced_text = " ".join(p.text for p in parts if hasattr(p, 'text') and p.text)
                if forced_text:
                    reply_text = forced_text
                else:
                    reply_text = "Disculpa, tuve un pequeño inconveniente procesando tu solicitud. ¿Me la repites?"
            except Exception as e_forced:
                logger.error("ai.forced_text_failed", error=str(e_forced))
                reply_text = "Disculpa, tuve un pequeño inconveniente procesando tu solicitud. ¿Me la repites?"

    except Exception as e:
        logger.error("ai.gemini_call_failed", error=str(e), phone=phone)
        reply_text = "Disculpá, en este momento el sistema está saturado. ¿Me podés volver a escribir en 5 minutos? 🙏"

    # 4. Save Gemini's response to Redis

    await session_mgr.add_message(phone, role="model", content=reply_text)

    logger.info("ai.route_message.success", phone=phone)
    return reply_text


# ── Ingestion (Admin) ────────────────────────────────────────────────────────

SYSTEM_PROMPT_INGESTION = """Tu tarea es leer la descripción técnica, el manual, el origen o cualquier texto "crudo" de un producto y transformarlo en un **Perfil de Venta Altamente Persuasivo**.
Extrae las características clave, identifica a qué público objetivo (target) le sirve más este producto, y construye posibles objeciones que tendría un comprador junto a tu mejor respuesta para rebatirlas.

REGLAS DE ROBUSTEZ:
1. Si te pasan un LINK (ej. de MercadoLibre o Amazon) con muchos parámetros técnicos, IGNORA los parámetros de rastreo y enfócate en el nombre y descripción que puedas deducir.
2. Si el texto o los archivos son escasos o de mala calidad, USA TU CONOCIMIENTO GENERAL sobre ese tipo de producto para completar el perfil (ej. si es una PS5, ya sabes qué es y para quién sirve).
3. NUNCA respondas con un error. Genera el mejor perfil posible con la info disponible.
"""

async def generate_sale_profile(name: str, description_raw: str, files: list[tuple[str, bytes, str]] = None) -> dict[str, Any]:
    """
    Uses Gemini Structured Outputs (response_schema) and Multimodality to analyze raw product text
    and any attached images/PDFs/documents. Returns a highly structured JSON strictly adhering to our Product model.
    """
    logger.info("ai.generate_sale_profile.start", product_name=name, has_files=bool(files))
    from pydantic import BaseModel, Field

    # Define the precise schema we want Gemini to output
    class ObjectionItem(BaseModel):
        objection: str = Field(description="La duda o problema del cliente (ej: 'Es muy caro')")
        response: str = Field(description="Tu respuesta persuasiva para rebatir esa objeción")

    class SaleProfileSchema(BaseModel):
        key_features: list[str] = Field(description="Un array con 3 a 5 beneficios o características principales muy vendedoras, claras y directas.")
        target_audience: str = Field(description="Una descripción breve del público ideal (ej: 'Familias con mascotas pequeñas' o 'Deportistas amateur').")
        objection_tree: list[ObjectionItem] = Field(description="Una lista de posibles objeciones del cliente y las respuestas recomendadas para convencerlo.")
        closing_script: str = Field(description="Una frase corta y poderosa para incitar a la compra inmediata.")

    # Prepare Multimodal Content
    contents = []
    
    # 1. Add any uploaded files (images, PDFs, text files)
    if files:
        for filename, file_bytes, mime_type in files:
            try:
                # Add file part directly. Gemini SDK handles conversion to base64.
                part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
                contents.append(part)
            except Exception as e:
                logger.warning("ai.generate_sale_profile.file_skipped", filename=filename, error=str(e))

    # 2. Add text prompt
    prompt = f"Producto: {name}\n\nTexto Crudo provisto por el proveedor o administrador:\n{description_raw}\n\nGenera el perfil de venta extrayendo la información del texto y de los archivos adjuntos, usando ESTRICTAMENTE el esquema JSON solicitado."
    contents.append(prompt)

    try:
        response = await client.aio.models.generate_content(
            model=settings.ai_stage1_model,  # We use the pro model for complex structured extraction
            contents=contents, # Now passing a list of mixed Parts (text + multimedia)
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_INGESTION,
                temperature=0.2, # Low temperature for analytical extraction
                response_mime_type="application/json",
                response_schema=SaleProfileSchema, 
            ),
        )
        
        # Parse the JSON string Gemini returned into a Python dict
        if response.text:
            profile_dict = json.loads(response.text)
            logger.info("ai.generate_sale_profile.success", product_name=name)
            return profile_dict
        
        return {}
            
    except Exception as e:
        logger.error("ai.generate_sale_profile.failed", product_name=name, error=str(e))
        return {}
