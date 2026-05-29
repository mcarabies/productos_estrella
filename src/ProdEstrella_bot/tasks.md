# Master Development Plan (tasks.md)

## Phase 1: Infraestructura y Setup Base
- [x] Configurar Docker Compose (App, PostgreSQL, Redis, Traefik).
- [x] Configurar Evolution API v2 para actuar como WhatsApp Web (Bypass de Meta).
- [x] Crear endpoints para webhooks de Evolution API (`/webhooks/whatsapp`).
- [x] Configurar Traefik como reverse proxy con SSL (Let's Encrypt).
- [x] Desplegar en el VPS (`productosestrella.club`).

## Phase 2: Integración de Pagos (Mercado Pago)
- [x] Crear endpoint de recepción de webhooks de Mercado Pago (`/webhooks/mercadopago`).
- [x] Configurar creación de Preferencias de pago y links (`app/payments/mercadopago.py`).
- [ ] Validar recepción de notificaciones de Mercado Pago en producción. (En proceso)
- [x] Actualizar el estado de la orden en la base de datos tras pago aprobado.
- [x] Notificar al cliente vía WhatsApp (Evolution API) que su pago ha sido recibido.

## Phase 3: Lógica AI (Gemini)
- [x] Configurar orquestador AI (Stage 1, Stage 2, Stage 3).
- [x] Implementar la generación de preferencias de MP desde el prompt de Gemini.
- [ ] Pruebas generales del flujo de Venta completo (Del saludo al pago).
- [x] Ajustar interacción inicial del bot (generar confianza, retrasar cierre y quitar "¿Tienen stock?").

## Phase 4: Acortador de URLs Propio
- [x] Crear modelo `ShortLink` en DB (`app/domain/models/short_link.py`).
- [x] Migración Alembic `0003_add_short_links.py` para crear tabla `short_links`.
- [x] Endpoint público `GET /r/{code}` que redirige al wa.me destino (`app/routers/public/redirect.py`).
- [x] Al crear un producto, genera automáticamente un short link de 7 caracteres y guarda la URL corta en `product.whatsapp_link`.
- [ ] Aplicar migración `0003` en producción (`alembic upgrade head`).

