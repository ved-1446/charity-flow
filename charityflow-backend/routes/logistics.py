from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from middleware.admin_only import admin_only
from models.activity_log import ActivityLogDB
from bson import ObjectId
from utils.serializers import serialize_date

# logistics_entries.donation_id is intentionally stored as a string representation of the donation ObjectId.
# This ensures cross-collection consistency, decouples reference semantics, and matches frontend query parameters without casting anomalies.
router = APIRouter(prefix="/logistics", tags=["logistics"])

@router.get("")
async def get_logistics(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.logistics_entries.find().sort("updated_at", -1)
    results = []
    async for entry in cursor:
        entry["_id"] = str(entry["_id"])
        # Consistent string type for donation_id
        donation_id_str = str(entry.get("donation_id", ""))
        entry["donation_id"] = donation_id_str
        if "updated_at" in entry:
            entry["updated_at"] = serialize_date(entry["updated_at"])

        entry["category"] = ""
        entry["description"] = ""
        entry["donor_email"] = ""
        entry["location"] = ""
        entry["assigned_ngo"] = ""
        entry["ngo_name"] = ""

        try:
            if donation_id_str:
                donation = await db.donations.find_one({"_id": ObjectId(donation_id_str)})
                if donation:
                    entry["category"] = donation.get("category", "") or ""
                    entry["description"] = donation.get("description", "") or ""
                    entry["donor_email"] = donation.get("donor_email", "") or ""
                    entry["location"] = donation.get("location", "") or ""
                    entry["assigned_ngo"] = donation.get("assigned_ngo", "") or ""

                    if entry["assigned_ngo"]:
                        ngo = await db.ngos.find_one({"email": entry["assigned_ngo"]})
                        if ngo:
                            entry["ngo_name"] = ngo.get("name", "") or ""
        except Exception:
            pass

        if "donation_details" in entry:
            del entry["donation_details"]

        results.append(entry)
    return results

class StageUpdate(BaseModel):
    stage: str

@router.patch("/{donation_id}")
async def update_logistics_stage(donation_id: str, payload: StageUpdate, request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    now = datetime.now(timezone.utc)
    try:
        donation_oid = ObjectId(donation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid donation ID format")

    donation_id_str = str(donation_id)

    if payload.stage == "undo_hub":
        await db.donations.update_one({"_id": donation_oid}, {"$set": {"status": "allocated"}})
        await db.logistics_entries.update_one(
            {"donation_id": donation_id_str},
            {"$set": {"stage": "picked_up", "updated_by": user["email"], "updated_at": now}}
        )
        log = ActivityLogDB(
            user_email=user["email"],
            action="undo_hub",
            details=f"Donation {donation_id_str} reverted from hub to picked up",
            timestamp=now
        )
        await db.activity_logs.insert_one(log.model_dump())
        return {"message": "Stage reverted to picked_up"}

    result = await db.logistics_entries.update_one(
        {"donation_id": donation_id_str},
        {"$set": {"stage": payload.stage, "updated_by": user["email"], "updated_at": now}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Logistics entry not found")

    if payload.stage == "delivered":
        await db.donations.update_one({"_id": donation_oid}, {"$set": {"status": "delivered"}})

    log = ActivityLogDB(
        user_email=user["email"],
        action="update",
        details=f"Logistics for {donation_id_str} moved to {payload.stage}",
        timestamp=now
    )
    await db.activity_logs.insert_one(log.model_dump())

    return {"message": f"Stage updated to {payload.stage}"}

class CancelDeliveryRequest(BaseModel):
    reason: str

@router.patch("/{donation_id}/cancel-delivery")
async def cancel_delivery(donation_id: str, payload: CancelDeliveryRequest, request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    now = datetime.now(timezone.utc)
    try:
        donation_oid = ObjectId(donation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid donation ID format")

    donation_id_str = str(donation_id)

    await db.donations.update_one({"_id": donation_oid}, {"$set": {"status": "allocated"}})
    result = await db.logistics_entries.update_one(
        {"donation_id": donation_id_str},
        {"$set": {"stage": "picked_up", "updated_by": user["email"], "updated_at": now}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Logistics entry not found")

    log = ActivityLogDB(
        user_email=user["email"],
        action="delivery_cancelled",
        details=f"Delivery cancelled for {donation_id_str}. Reason: {payload.reason}. By: {user['email']}",
        timestamp=now
    )
    await db.activity_logs.insert_one(log.model_dump())

    return {"message": "Delivery cancelled successfully"}
