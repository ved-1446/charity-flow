from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from middleware.admin_only import admin_only
from models.activity_log import ActivityLogDB
from bson import ObjectId

router = APIRouter(prefix="/logistics", tags=["logistics"])

@router.get("")
async def get_logistics(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.logistics_entries.find().sort("updated_at", -1)
    results = []
    async for entry in cursor:
        entry["_id"] = str(entry["_id"])
        # Ensure donation_id is string
        entry["donation_id"] = str(entry.get("donation_id", ""))
        entry["category"] = ""
        entry["description"] = ""
        entry["donor_email"] = ""
        entry["location"] = ""
        entry["assigned_ngo"] = ""
        entry["ngo_name"] = ""
        try:
            if entry["donation_id"]:
                donation = await db.donations.find_one({"_id": ObjectId(entry["donation_id"])})
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
    try:
        donation_oid = ObjectId(donation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid donation ID format")
    if payload.stage == "undo_hub":
        await db.donations.update_one({"_id": donation_oid}, {"$set": {"status": "allocated"}})
        await db.logistics_entries.update_one(
            {"donation_id": donation_id},
            {"$set": {"stage": "picked_up", "updated_by": user["email"], "updated_at": __import__('datetime').datetime.utcnow()}}
        )
        log = ActivityLogDB(
            user_email=user["email"],
            action="undo_hub",
            details=f"Donation {donation_id} reverted from hub to picked up"
        )
        await db.activity_logs.insert_one(log.model_dump())
        return {"message": "Stage reverted to picked_up"}

    result = await db.logistics_entries.update_one(
        {"donation_id": donation_id},
        {"$set": {"stage": payload.stage, "updated_by": user["email"], "updated_at": __import__('datetime').datetime.utcnow()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Logistics entry not found")
        
    if payload.stage == "delivered":
        await db.donations.update_one({"_id": donation_oid}, {"$set": {"status": "delivered"}})
        
    log = ActivityLogDB(
        user_email=user["email"],
        action="update",
        details=f"Logistics for {donation_id} moved to {payload.stage}"
    )
    await db.activity_logs.insert_one(log.model_dump())
    
    return {"message": f"Stage updated to {payload.stage}"}

class CancelDeliveryRequest(BaseModel):
    reason: str

@router.patch("/{donation_id}/cancel-delivery")
async def cancel_delivery(donation_id: str, payload: CancelDeliveryRequest, request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    try:
        donation_oid = ObjectId(donation_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid donation ID format")
        
    await db.donations.update_one({"_id": donation_oid}, {"$set": {"status": "allocated"}})
    await db.logistics_entries.update_one(
        {"donation_id": donation_id},
        {"$set": {"stage": "picked_up", "updated_by": user["email"], "updated_at": __import__('datetime').datetime.utcnow()}}
    )
    
    log = ActivityLogDB(
        user_email=user["email"],
        action="delivery_cancelled",
        details=f"Delivery cancelled for {donation_id}. Reason: {payload.reason}. By: {user['email']}"
    )
    await db.activity_logs.insert_one(log.model_dump())
    
    return {"message": "Delivery cancelled successfully"}
