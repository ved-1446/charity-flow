import os
import asyncio
from datetime import datetime, timezone, time
from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
from middleware.admin_only import admin_only
from models.logistics import LogisticsEntryDB
from models.activity_log import ActivityLogDB
from bson import ObjectId
from config import DEMO_MODE, DEMO_DELIVERY_DELAY_SECONDS
from utils.serializers import serialize_date

router = APIRouter(prefix="/admin", tags=["admin"])

async def simulate_delivery(donation_id: str, db):
    delay_seconds = DEMO_DELIVERY_DELAY_SECONDS

    # Step 1: to hub
    await asyncio.sleep(delay_seconds)
    now = datetime.now(timezone.utc)
    await db.donations.update_one({"_id": ObjectId(donation_id)}, {"$set": {"status": "at_hub"}})
    await db.logistics_entries.update_one(
        {"donation_id": str(donation_id)},
        {"$set": {"stage": "at_hub", "updated_at": now}}
    )

    log1 = ActivityLogDB(
        user_email="system@demo.org",
        action="auto_delivery",
        details=f"Donation {donation_id} arrived at hub",
        timestamp=now
    )
    await db.activity_logs.insert_one(log1.model_dump())

    # Step 2: delivered
    await asyncio.sleep(delay_seconds)
    now2 = datetime.now(timezone.utc)
    await db.donations.update_one({"_id": ObjectId(donation_id)}, {"$set": {"status": "delivered"}})
    await db.logistics_entries.update_one(
        {"donation_id": str(donation_id)},
        {"$set": {"stage": "delivered", "updated_at": now2}}
    )

    log2 = ActivityLogDB(
        user_email="system@demo.org",
        action="auto_delivery",
        details=f"Donation {donation_id} delivered successfully",
        timestamp=now2
    )
    await db.activity_logs.insert_one(log2.model_dump())

@router.get("/stats")
async def get_stats(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    pending_count = await db.donations.count_documents({"status": "pending"})
    ngo_count = await db.ngos.count_documents({})
    delivered_count = await db.donations.count_documents({"status": "delivered"})
    return {
        "pending_count": pending_count,
        "ngo_count": ngo_count,
        "delivered_count": delivered_count
    }

@router.get("/actions-today")
async def get_actions_today(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    now_utc = datetime.now(timezone.utc)
    # Start of day in UTC
    start_of_day = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    count = await db.activity_logs.count_documents({"timestamp": {"$gte": start_of_day}})
    return {"actions_today": count}

@router.get("/users")
async def get_users(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.users.find({}, {"password_hash": 0})
    users = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        if "created_at" in document:
            document["created_at"] = serialize_date(document["created_at"])
        users.append(document)
    return users

@router.get("/ngos")
async def get_ngos(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.ngos.find({})
    ngos = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        ngos.append(document)
    return ngos

class AllocationRequest(BaseModel):
    donation_id: str
    ngo_email: str

@router.post("/allocate")
async def allocate(
    payload: AllocationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict = Depends(admin_only)
):
    db = request.app.state.db
    now = datetime.now(timezone.utc)

    try:
        oid = ObjectId(payload.donation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid donation ID format")

    donation = await db.donations.find_one({"_id": oid})
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    await db.donations.update_one(
        {"_id": oid},
        {"$set": {"status": "allocated", "assigned_ngo": payload.ngo_email}}
    )

    # donation_id stored as string representation of ObjectId
    entry = LogisticsEntryDB(
        donation_id=str(payload.donation_id),
        stage="picked_up",
        updated_by=user["email"],
        updated_at=now
    )
    await db.logistics_entries.insert_one(entry.model_dump())

    log = ActivityLogDB(
        user_email=user["email"],
        action="allocation",
        details=f"Donation {payload.donation_id} allocated to {payload.ngo_email}",
        timestamp=now
    )
    await db.activity_logs.insert_one(log.model_dump())

    if DEMO_MODE:
        background_tasks.add_task(simulate_delivery, payload.donation_id, db)

    return {"message": "Allocated successfully"}

@router.get("/my-activity")
async def my_activity(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.activity_logs.find({"user_email": user["email"]}).sort("timestamp", -1).limit(10)
    logs = []
    async for entry in cursor:
        logs.append({
            "action": entry.get("action", ""),
            "details": entry.get("details", ""),
            "timestamp": serialize_date(entry.get("timestamp"))
        })
    return logs

@router.get("/all-activity")
async def all_activity(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.activity_logs.find().sort("timestamp", -1)
    logs = []
    async for entry in cursor:
        logs.append({
            "user_email": entry.get("user_email", ""),
            "action": entry.get("action", ""),
            "details": entry.get("details", ""),
            "timestamp": serialize_date(entry.get("timestamp"))
        })
    return logs

@router.post("/reset-test-data")
async def reset_test_data(request: Request, user: dict = Depends(admin_only)):
    if not DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reset test data is disabled when DEMO_MODE is false"
        )
    db = request.app.state.db
    await db.donations.delete_many({})
    await db.logistics_entries.delete_many({})
    await db.activity_logs.delete_many({})
    await db.contact_messages.delete_many({})
    return {"message": "Test data cleared successfully"}
