import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from models.ngo import NGODB
from config import MONGO_URI

ngos_data = [
  { "name": "Helping Hands Trust", "email": "helpinghands@demo.ngo",
    "requested_items": ["Blankets", "Clothes"], "location": "Pune, MH",
    "reason": "Winter relief for flood-affected families", "status": "verified" },
  { "name": "Bright Futures Foundation", "email": "brightfutures@demo.ngo",
    "requested_items": ["Books", "Stationery"], "location": "Mumbai, MH",
    "reason": "Rural education project for underprivileged children", "status": "verified" },
  { "name": "Relief India Trust", "email": "relief@demo.ngo",
    "requested_items": ["Utensils", "Food"], "location": "Nagpur, MH",
    "reason": "Monsoon emergency aid distribution", "status": "verified" },
  { "name": "Udaan NGO", "email": "udaan@demo.ngo",
    "requested_items": ["Toys", "Electronics"], "location": "Delhi, NCR",
    "reason": "Child development and recreation program", "status": "verified" },
  { "name": "Sahayata Foundation", "email": "sahayata@demo.ngo",
    "requested_items": ["Clothes", "Toys"], "location": "Hyderabad, TS",
    "reason": "Hygiene and welfare drive for shelter homes", "status": "verified" }
]

async def seed_ngos(db=None):
    client = None
    if db is None:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client.get_default_database()

    seeded_count = 0
    skipped_count = 0

    for data in ngos_data:
        email = data["email"].strip().lower()
        # Idempotent: skip existing NGO, never duplicate
        existing = await db.ngos.find_one({"email": email})
        if existing:
            skipped_count += 1
            continue

        ngo = NGODB(**data)
        await db.ngos.insert_one(ngo.model_dump())
        seeded_count += 1

    print(f"Seed NGOs complete: {seeded_count} inserted, {skipped_count} skipped.")
    if client:
        client.close()

if __name__ == "__main__":
    asyncio.run(seed_ngos())
