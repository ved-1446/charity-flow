import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.hash import bcrypt
from models.user import UserDB
from config import MONGO_URI, SEED_ADMIN_PASSWORD, SEED_DONOR_PASSWORD

users_data = [
    # Admins
    {
        "email": "admin@charityflow.org",
        "default_password": "Admin@1234",
        "role": "admin",
        "status": "active"
    },
    {
        "email": "admin2@charityflow.org",
        "default_password": "Admin@5678",
        "role": "admin",
        "status": "active"
    },
    {
        "email": "admin3@charityflow.org",
        "default_password": "Admin@9012",
        "role": "admin",
        "status": "active"
    },
    # Donors
    {
        "email": "donor@charityflow.org",
        "default_password": "Donor@1234",
        "role": "donor",
        "status": "active"
    },
    {
        "email": "donor2@charityflow.org",
        "default_password": "Donor@5678",
        "role": "donor",
        "status": "active"
    },
    {
        "email": "donor3@charityflow.org",
        "default_password": "Donor@9012",
        "role": "donor",
        "status": "active"
    },
    {
        "email": "donor4@charityflow.org",
        "default_password": "Donor@3456",
        "role": "donor",
        "status": "active"
    },
    {
        "email": "donor5@charityflow.org",
        "default_password": "Donor@7890",
        "role": "donor",
        "status": "active"
    },
    {
        "email": "donor6@charityflow.org",
        "default_password": "Donor@2345",
        "role": "donor",
        "status": "active"
    }
]

async def seed_users(db=None):
    client = None
    if db is None:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client.get_default_database()

    seeded_count = 0
    skipped_count = 0

    for data in users_data:
        email = data["email"].strip().lower()
        role = data["role"]

        # Password override check
        if role == "admin" and SEED_ADMIN_PASSWORD:
            password = SEED_ADMIN_PASSWORD
        elif role == "donor" and SEED_DONOR_PASSWORD:
            password = SEED_DONOR_PASSWORD
        else:
            password = data["default_password"]

        # Idempotent: skip existing user, never duplicate
        existing = await db.users.find_one({"email": email})
        if existing:
            skipped_count += 1
            continue

        hashed = bcrypt.hash(password)
        user = UserDB(
            email=email,
            password_hash=hashed,
            role=role,
            status=data["status"]
        )
        await db.users.insert_one(user.model_dump())
        seeded_count += 1

    print(f"Seed users complete: {seeded_count} inserted, {skipped_count} skipped.")
    if client:
        client.close()

if __name__ == "__main__":
    asyncio.run(seed_users())
