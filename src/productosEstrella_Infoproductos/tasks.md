# Master Development Plan - Productos Estrella

## Fase 1: Backend FastAPI
- [x] `main.py` — Motor dinámico: router de landings, catálogo Home, inyección de scripts
- [x] `requirements.txt` — Dependencias del proyecto

## Fase 2: Templates HTML
- [x] `templates/home.html` — Catálogo con Tailwind CDN + filtros Alpine.js
- [x] `templates/404.html` — Página 404 personalizada
- [x] `shared/scripts_header.html` — Placeholder para píxeles de tracking

## Fase 3: Estructura de Productos
- [x] `products/guia-productividad/meta.json` — Ejemplo de metadata
- [x] `products/guia-productividad/index.html` — Landing de ejemplo
- [x] `products/el-arte-del-sueño-profundo/` — Nueva landing premium de Biohacking

## Fase 4: Docker & Infraestructura
- [x] `Dockerfile` — Imagen del contenedor FastAPI
- [x] `docker-compose.yml` — Stack con Traefik + SSL Let's Encrypt
- [x] `traefik/traefik.yml` — Config estática de Traefik
- [x] `traefik/acme.json` — Archivo para certificados (vacío, permisos 600)

## Fase 5: Documentación y CI/CD
- [x] `DEPLOY.md` — Guía de despliegue en VPS Contabo
- [x] Implementar Workflow de Git (Github -> VPS)
- [x] Crear script `deploy.sh` de automatización
- [x] Actualizar `DEPLOY.md` con instrucciones de Git

## Fase 6: Expansión e Integraciones
- [x] Conectar MCP de Google Stitch para diseño asistido.
- [x] Actualizar landing "El Arte del Sueño Profundo" con Navbar persistente.
- [x] Añadir Social Proof (Reviews) y mejorar posicionamiento del mockup en Hero.
- [x] Rediseño de Bento Grid de Beneficios con assets 3D minimalistas.
- [x] Implementar sistema de notificaciones de pruebas sociales (Purchase Chips).
- [x] Actualización de todos los CTA con precio y enlace de pago directo.
- [ ] Integrar pasarela de pagos completa (Mercado Pago Avanzado).
- [ ] Configurar notificaciones vía WhatsApp para ventas.

## Fase 7: Optimización PageSpeed & UX
- [x] Corregir Robot.txt (eliminar HTML residual y añadir directivas reales).
- [x] Refactorizar Landing: Separar CSS y JS en archivos independientes.
- [x] Mejorar contrastes de accesibilidad (clases .biological-clarity, .mental-fog, footer).
- [x] Optimizar imágenes: Añadir atributos width/height y loading="lazy").
- [x] Añadir Meta Description y Landmarks semánticos ( <main> ).
- [x] Minificar assets y mejorar caché.
- [x] Corregir errores de parsing CSS en catálogo home.html (Alpine.js binding).


## Fase 8: Compliance & TikTok Ads
- [x] Crear Página de Política de Privacidad (el-arte-del-sueno-profundo).
- [x] Crear Página de Términos y Condiciones (el-arte-del-sueno-profundo).
- [x] Actualizar Footer con Links y Correo de Soporte.

## Fase 9: Mailcow & Infraestructura de Correo
- [ ] Clonar mailcow-dockerized en `/opt/mailcow-dockerized`
- [ ] Configurar `mailcow.conf` con enlace a Traefik y Skip LE
- [ ] Crear `docker-compose.override.yml` para integración de red y labels
- [ ] Configurar Registros DNS (A, MX, SPF, DKIM, DMARC)
## Fase 10: Optimización de Copy y Conversión
- [x] Actualizar todos los CTA a "DESCARGAR EBOOK AHORA" y eliminar referencias de precios.
- [x] Añadir leyenda "Pagá en pesos y por Mercado Pago" con su respectivo logo.
- [x] Reordenar sección Hero en dispositivos móviles para priorizar la imagen del mockup.
