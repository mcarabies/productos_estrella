import asyncio
from sqlalchemy.future import select
from sqlalchemy import delete
from app.core.database import AsyncSessionLocal
from app.domain.models import Conversation

async def clear_history():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Conversation))
        await db.commit()
        print("Historial de conversaciones borrado con éxito.")

if __name__ == "__main__":
    asyncio.run(clear_history())
