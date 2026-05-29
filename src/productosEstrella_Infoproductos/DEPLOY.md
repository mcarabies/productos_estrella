# 🚀 Guía de Despliegue — Productos Estrella
## VPS Contabo (Ubuntu 22.04 limpio)

---

## PASO 1 — Entrar al VPS por SSH

Desde tu PC:
```bash
ssh root@147.93.2.187
```
Te va a pedir la contraseña de root que Contabo te envió por email.

---

## PASO 2 — Instalar Docker

Una sola línea que instala todo:
```bash
curl -fsSL https://get.docker.com | bash
```

Verificar que quedó instalado:
```bash
docker --version
```
Debe decir algo como `Docker version 26.x.x`.

---

## PASO 3 — Clonar el proyecto

```bash
cd /root
git clone https://github.com/mcarabies/productosestrella_infoproductos.git app
cd /root/app
```

El proyecto vive en `/root/app`. Simple, directo.

---

## PASO 4 — Preparar el archivo de certificados SSL

```bash
chmod 600 /root/app/traefik/acme.json
```

> ⚠️ Sin esto Traefik falla al arrancar.

---

## PASO 5 — Levantar el sistema

```bash
cd /root/app
docker compose up -d --build
```

Esperar a que termine (descarga imágenes y compila). Al final debe decir:
```
✔ Container traefik                Started
✔ Container productos_estrella_app Started
```

Verificar que están corriendo:
```bash
docker compose ps
```

---

## PASO 6 — Verificar que funciona

```bash
# Prueba local en el VPS (debe responder {"status":"ok"})
curl http://localhost:8000/health
```

Si responde OK, en unos minutos el SSL se genera y el sitio queda en:
👉 **https://productosestrella.club**

---

## CÓMO AGREGAR UN NUEVO EBOOK

No se reinicia Docker — los cambios son inmediatos.

```bash
# Crear la carpeta del nuevo producto
mkdir -p /root/app/products/nombre-del-ebook

# Crear la metadata
nano /root/app/products/nombre-del-ebook/meta.json
```

Pegar este JSON y completar los datos:
```json
{
  "titulo": "Nombre del Ebook",
  "descripcion_corta": "Una descripción corta de máx 2 líneas.",
  "categoria": "Productividad",
  "precio": "$9.99 USD",
  "url_hotmart": "https://go.hotmart.com/TU_LINK",
  "orden_prioridad": 1
}
```

Luego subir `index.html` (landing) y `thumbnail.jpg` via SCP o FTP.

---

## CÓMO ACTUALIZAR EL CÓDIGO (Workflow Git)

Cuando hagas cambios en tu PC y los subas a GitHub:

**Desde tu PC:**
```bash
git add .
git commit -m "descripción del cambio"
git push origin main
```

**En el VPS:**
```bash
ssh root@147.93.2.187
# Ingresa tu contraseña de VPS
cd /root/app
git pull origin main
# Ingresa tu token personal de GitHub (ghp_...)
docker compose up -d --build
```

O usar el script de automatización:
```bash
bash /root/app/scripts/deploy.sh
```

---

## COMANDOS DE MANTENIMIENTO

```bash
# Ver logs en vivo
docker compose logs -f app

# Reiniciar solo el app (sin Traefik)
docker compose restart app

# Ver estado de los contenedores
docker compose ps

# Apagar todo
docker compose down
```

---

## ❌ SI ALGO FALLA

```bash
# Ver qué error dio al iniciar
docker compose logs traefik
docker compose logs app
```


---

## 🏗️ Fase 1: Configuración Local (Tu PC)

Sigue estos pasos para subir tu código a GitHub por primera vez.

1. **Inicializar Git localmente**
   Abre una terminal en la carpeta del proyecto y ejecuta:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Proyecto Productos Estrella"
   ```

2. **Crear el Repositorio en GitHub**
   - Ve a [github.com/new](https://github.com/new).
   - Nombre: `productos-estrella` (público o privado).
   - **NO** marques "Initialize this repository with a README".
   - Haz clic en **Create repository**.

3. **Vincular y Subir**
   Copia los comandos que te da GitHub, parecidos a estos:
   ```bash
   git remote add origin https://github.com/TU_USUARIO/productos-estrella.git
   git branch -M main
   git push -u origin main
   ```

---

## 🌐 Fase 2: Configuración en el VPS (Contabo)

### 1. Requisitos previos
- Ubuntu 22.04 LTS con Docker instalado (`curl -fsSL https://get.docker.com | bash`).
- Dominio `productosestrella.club` apuntando a la IP del VPS.

### 2. Clonar el repositorio
```bash
# Crear carpeta de apps si no existe
mkdir -p /opt/apps && cd /opt/apps

# Clonar el proyecto
git clone https://github.com/TU_USUARIO/productos-estrella.git
cd productos-estrella
```

### 3. Preparar permisos y certificados
```bash
# Crear acme.json con permisos restrictivos para SSL
mkdir -p traefik
touch traefik/acme.json
chmod 600 traefik/acme.json
```

### 4. Primer despliegue
```bash
docker compose up -d --build
```

---

## ⚡ Fase 3: Automatización del Despliegue (Actualizaciones)

Para no tener que escribir comandos largos cada vez, usaremos un script de automatización.

### 1. El script `deploy.sh`
Asegúrate de que el archivo `scripts/deploy.sh` existe (se incluye en el proyecto). Si no, créalo:
```bash
#!/bin/bash
echo "🚀 Iniciando despliegue..."
git pull origin main
docker compose up -d --build
echo "✅ Despliegue completado con éxito."
```

### 2. Cómo actualizar el sitio
Cada vez que hagas un cambio en tu PC y quieras verlo en el VPS:

**En tu PC:**
```bash
git add .
git commit -m "Descripción del cambio"
git push origin main
```

**En el VPS:**
```bash
./scripts/deploy.sh
```

---

## 📂 Estructura de Archivos en Producción

```
/opt/apps/productos-estrella/
├── main.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── scripts/
│   └── deploy.sh         ← Script de actualización
├── traefik/
│   ├── traefik.yml
│   └── acme.json         ← Permisos 600 requeridos
├── templates/            ← Home y 404
├── shared/               ← Tracking pixels
└── products/             ← Tus Ebooks (persistent)
```

---

## 🛠️ Mantenimiento Útil

- **Ver logs del sistema:** `docker compose logs -f app`
- **Verificar SSL:** `curl -vI https://productosestrella.club`
- **Agregar Ebooks:** Simplemente crea la subcarpeta en `products/` y el sistema la detectará al instante sin reiniciar.
