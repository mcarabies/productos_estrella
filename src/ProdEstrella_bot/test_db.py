import asyncio
from sqlalchemy.future import select
from sqlalchemy import or_
from app.core.database import AsyncSessionLocal
from app.domain.models import Product

async def test_search():
    nombre_o_categoria = "lápiz negro"
    search_term = nombre_o_categoria.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")

    async with AsyncSessionLocal() as db:
        stmt = select(Product).where(
            Product.is_active == True,
            or_(
                Product.name.ilike(f"%{nombre_o_categoria}%"),
                Product.name.ilike(f"%{search_term}%"),
            )
        )
        result = await db.execute(stmt)
        products = result.scalars().all()
        print(f"Buscando '{nombre_o_categoria}' o '{search_term}': encontrados {len(products)}")

asyncio.run(test_search())
