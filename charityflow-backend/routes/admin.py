import os
import asyncio
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from middleware.admin_only import admin_only
from models.logistics import LogisticsEntryDB
from models.activity_log import ActivityLogDB
from bson import ObjectId

router = APIRouter(prefix="/admin", tags=["admin"])

async def simulate_delivery(donation_id: str, db):
    delay_seconds = int(os.getenv("DEMO_DELIVERY_DELAY_SECONDS", "90"))
    
    # Step 1
    await asyncio.sleep(delay_seconds)
    await db.donations.update_one({"_id": ObjectId(donation_id)}, {"$set": {"status": "at_hub"}})
    await db.logistics_entries.update_one(
        {"donation_id": donation_id},
        {"$set": {"stage": "at_hub", "updated_at": __import__('datetime').datetime.utcnow()}}
    )
    
    log1 = ActivityLogDB(
        user_email="system@demo.org",
        action="auto_delivery",
        details=f"Donation {donation_id} arrived at hub"
    )
    await db.activity_logs.insert_one(log1.model_dump())
    
    # Step 2
    await asyncio.sleep(delay_seconds)
    await db.donations.update_one({"_id": ObjectId(donation_id)}, {"$set": {"status": "delivered"}})
    await db.logistics_entries.update_one(
        {"donation_id": donation_id},
        {"$set": {"stage": "delivered", "updated_at": __import__('datetime').datetime.utcnow()}}
    )
    
    log2 = ActivityLogDB(
        user_email="system@demo.org",
        action="auto_delivery",
        details=f"Donation {donation_id} delivered successfully"
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
    from datetime import datetime, time
    now_utc = datetime.utcnow()
    start_of_day = datetime.combine(now_utc.date(), time.min)
    count = await db.activity_logs.count_documents({"timestamp": {"$gte": start_of_day}})
    return {"actions_today": count}

@router.get("/users")
async def get_users(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.users.find({}, {"password_hash": 0})
    users = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
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
    
    await db.donations.update_one(
        {"_id": ObjectId(payload.donation_id)},
        {"$set": {"status": "allocated", "assigned_ngo": payload.ngo_email}}
    )
    
    entry = LogisticsEntryDB(
        donation_id=payload.donation_id,
        stage="picked_up",
        updated_by=user["email"]
    )
    await db.logistics_entries.insert_one(entry.model_dump())
    
    log = ActivityLogDB(
        user_email=user["email"],
        action="allocation",
        details=f"Donation {payload.donation_id} allocated to {payload.ngo_email}"
    )
    await db.activity_logs.insert_one(log.model_dump())
    
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        background_tasks.add_task(simulate_delivery, payload.donation_id, db)
        
    return {"message": "Allocated successfully"}

@router.get("/my-activity")
async def my_activity(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.activity_logs.find({"user_email": user["email"]}).sort("timestamp", -1).limit(10)
    logs = []
    async for entry in cursor:
        timestamp_str = entry["timestamp"].strftime("%Y-%m-%d %H:%M") if "timestamp" in entry and entry["timestamp"] else ""
        logs.append({
            "action": entry.get("action", ""),
            "details": entry.get("details", ""),
            "timestamp": timestamp_str
        })
    return logs

@router.get("/all-activity")
async def all_activity(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.activity_logs.find().sort("timestamp", -1)
    logs = []
    async for entry in cursor:
        timestamp_str = entry["timestamp"].strftime("%Y-%m-%d %H:%M") if "timestamp" in entry and entry["timestamp"] else ""
        logs.append({
            "user_email": entry.get("user_email", ""),
            "action": entry.get("action", ""),
            "details": entry.get("details", ""),
            "timestamp": timestamp_str
        })
    return logs

@router.post("/reset-test-data")
async def reset_test_data(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    await db.donations.delete_many({})
    await db.logistics_entries.delete_many({})
    await db.activity_logs.delete_many({})
    await db.contact_messages.delete_many({})
    return {"message": "Test data cleared successfully"}
