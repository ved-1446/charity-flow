import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI
from seed.seed_users import seed_users
from seed.seed_ngos import seed_ngos

async def seed_all():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
    print("=== SEEDING CHARITY FLOW DATABASE ===")
    await seed_users(db)
    await seed_ngos(db)
    client.close()
    print("=== ALL SEEDING FINISHED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(seed_all())

