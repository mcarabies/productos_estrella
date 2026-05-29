"""
Database Seed Script — Phase 2 Sandbox
Injects dummy products into PostgreSQL so Gemini can "lookup" products.
"""
import asyncio
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal
from app.domain.models.product import Product


async def seed_products():
    print("Seed: Inicializando productos...")
    async with AsyncSessionLocal() as db:
        # Check if products exist
        result = await db.execute(select(Product))
        if result.scalars().first():
            print("Seed: La base de datos ya tiene productos. Terminando.")
            return

        p1 = Product(
            name="Sillón esquinero Premium",
            description_raw="Sillón de 3 cuerpos de tela anti-desgarros, ideal para mascotas y familia. Colores gris y beige.",
            price=350000.0,
            currency="ARS",
            stock=12,
            is_active=True,
            sale_profile={
                "key_features": ["Tela anti-desgarro", "Soporta mascotas", "Patas de madera maciza", "3 Cuerpos"],
                "target_audience": "Familias de clase media con mascotas",
                "objection_tree": {
                    "precio": "Es una inversión para 10 años, además la tela se banca cualquier rasguño, a la larga ahorras.",
                    "envío": "Te lo enviamos gratis a capital y a precios re bajos a provincia."
                },
                "pricing_tiers": [{"label": "Lista", "price": 350000}, {"label": "Efectivo", "price": 300000}]
            }
        )

        p2 = Product(
            name="Auriculares In-Ear Bluetooth Estrella",
            description_raw="Auriculares in-ear tipo pod, batería de 24 hs, cancelación de ruido activa.",
            price=45000.0,
            currency="ARS",
            stock=5,
            is_active=True,
            sale_profile={
                "key_features": ["Cancelación de ruido (ANC)", "Batería dura 6h continuas, 24h con estuche", "Bluetooth 5.3"],
                "target_audience": "Gente que entrena, va al gimnasio, o viaja en transporte público",
                "objection_tree": {
                    "marca": "Es nuestra propia línea ensamblada con las mismas piezas de los modelos conocidos que valen el triple. Tienen 6 meses de garantía.",
                    "precio": "Para un auricular con ANC real (cancelación de sonido), este precio no existe en Argentina hoy."
                },
                "pricing_tiers": [{"label": "Lista", "price": 45000}, {"label": "Efectivo", "price": 40000}]
            }
        )

        db.add_all([p1, p2])
        await db.commit()
        print("Seed: ¡Agregados 2 productos de prueba (Sillón y Auriculares) a PostgreSQL! 🚀")


if __name__ == "__main__":
    asyncio.run(seed_products())
