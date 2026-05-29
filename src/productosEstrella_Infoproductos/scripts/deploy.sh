#!/bin/bash
# -------------------------------------------------------------------
#  Script de Despliegue Automatizado — Productos Estrella
# -------------------------------------------------------------------

# Colores para la terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Iniciando despliegue de Productos Estrella...${NC}"

# 1. Obtener cambios de GitHub
echo -e "${BLUE}📥 Bajando cambios desde GitHub...${NC}"
git pull origin main

# 2. Re-construir y levantar contenedores
echo -e "${BLUE}🏗️ Re-construyendo imágenes y levantando servicios...${NC}"
docker compose up -d --build

# 3. Limpieza de imágenes huérfanas
echo -e "${BLUE}🧹 Limpiando imágenes antiguas...${NC}"
docker image prune -f

echo -e "${GREEN}✅ Despliegue completado con éxito.${NC}"
echo -e "${GREEN}🌐 Sitio activo en: https://productosestrella.club${NC}"
