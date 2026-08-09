import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from models.ngo import NGODB
from dotenv import load_dotenv

load_dotenv()

async def get_db():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/charityflow")
    client = AsyncIOMotorClient(uri)
    return client.get_default_database()

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

async def seed():
    db = await get_db()
    for data in ngos_data:
        ngo = NGODB(**data)
        await db.ngos.update_one(
            {"email": ngo.email},
            {"$set": ngo.model_dump()},
            upsert=True
        )
    print("Seed complete: NGOs inserted.")

if __name__ == "__main__":
    asyncio.run(seed())
