import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from models.user import UserDB
from passlib.hash import bcrypt
from dotenv import load_dotenv

load_dotenv()

async def get_db():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/charityflow")
    client = AsyncIOMotorClient(uri)
    return client.get_default_database()

users_data = [
    {
        "email": "admin@charityflow.org",
        "password": "Admin@1234",
        "role": "admin",
        "status": "active"
    },
    {
        "email": "donor@charityflow.org",
        "password": "Donor@1234",
        "role": "donor",
        "status": "active"
    }
]

async def seed():
    db = await get_db()
    for data in users_data:
        hashed = bcrypt.hash(data["password"])
        user = UserDB(
            email=data["email"],
            password_hash=hashed,
            role=data["role"],
            status=data["status"]
        )
        await db.users.update_one(
            {"email": user.email},
            {"$set": user.model_dump()},
            upsert=True
        )
    print("Seed complete: Users inserted.")

if __name__ == "__main__":
    asyncio.run(seed())
