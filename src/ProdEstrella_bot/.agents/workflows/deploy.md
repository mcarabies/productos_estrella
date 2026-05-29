---
description: Deploy a producción del bot ProdEstrella en el VPS
---

# Deploy a Producción — ProdEstrella Bot

## Prerequisitos
- Acceso SSH al VPS configurado (usa el alias o IP del servidor)
- Cambios commiteados y pusheados a `main` en GitHub

---

## Paso 1 — Commit y push de los cambios locales

```bash
git add -A
git commit -m "feat: descripción del cambio"
git push origin main
```

## Paso 2 — Conectarse al VPS por SSH

```bash
ssh root@productosestrella.club
```

O si tenés alias configurado:
```bash
ssh vps-estrella
```

## Paso 3 — Ir al directorio del proyecto en el VPS

```bash
cd /opt/prodEstrella-bot
```

## Paso 4 — Traer los cambios de GitHub

```bash
git pull origin main
```

## Paso 5 — Rebuild y restart del contenedor de la app

```bash
docker compose build app
docker compose up -d app
```

> Si hubo cambios en **docker-compose.yml** (ej: nuevos routers Traefik), reiniciar también Traefik:
> ```bash
> docker compose up -d traefik
> ```

## Paso 6 — Correr migraciones de Alembic (si hay nuevas)

```bash
docker compose exec app alembic upgrade head
```

> **Siempre** correr este comando cuando hay una nueva migración en `migrations/versions/`.
> Es idempotente — no hace nada si ya está al día.

## Paso 7 — Verificar que todo esté corriendo

```bash
docker compose ps
docker compose logs app --tail=50
```

## Paso 8 — Probar el endpoint de salud

```bash
curl https://api.productosestrella.club/health
```

Debe responder: `{"status":"ok","version":"0.1.0"}`

---

## Rollback rápido (si algo falla)

```bash
git revert HEAD
git push origin main
# En el VPS:
git pull origin main
docker compose build app && docker compose up -d app
```

---

## Variables de entorno nuevas (.env en el VPS)

Si agregaste nuevas variables al `.env.example`, también tenés que agregarlas al `.env` real del VPS:

```bash
nano /opt/prodEstrella-bot/.env
```

Variables agregadas recientemente:
- `LINK_DOMAIN=product.productosestrella.club`
