import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from middleware.auth import get_current_user
from middleware.admin_only import admin_only
from models.donation import DonationDB
from models.activity_log import ActivityLogDB
from bson import ObjectId
from pydantic import BaseModel

router = APIRouter(tags=["donations"])

@router.post("/donate")
async def create_donation(
    request: Request,
    location: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    donorEmail: str = Form(...),
    photos: List[UploadFile] = File(...)
):
    db = request.app.state.db
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    saved_photos = []
    
    for photo in photos:
        ext = os.path.splitext(photo.filename)[1]
        new_filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(upload_dir, new_filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        saved_photos.append(f"uploads/{new_filename}")
        
    donation = DonationDB(
        donor_email=donorEmail,
        location=location,
        category=category,
        description=description,
        photos=saved_photos,
        status="pending"
    )
    
    result = await db.donations.insert_one(donation.model_dump())
    donation_id = str(result.inserted_id)
    
    log = ActivityLogDB(
        user_email=donorEmail,
        action="donation",
        details=f"New donation submitted with {len(saved_photos)} photos"
    )
    await db.activity_logs.insert_one(log.model_dump())
    
    return {"message": "Donation submitted successfully", "donation_id": donation_id}

@router.get("/donations")
async def get_donations(request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    cursor = db.donations.find().sort("created_at", -1)
    donations = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        donations.append(document)
    return donations

@router.get("/donations/{id}")
async def get_donation(id: str, request: Request, user: dict = Depends(get_current_user)):
    db = request.app.state.db
    try:
        doc = await db.donations.find_one({"_id": ObjectId(id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    if not doc:
        raise HTTPException(status_code=404, detail="Donation not found")
    doc["_id"] = str(doc["_id"])
    return doc

class StatusUpdate(BaseModel):
    status: str

@router.patch("/donations/{id}/status")
async def update_status(id: str, payload: StatusUpdate, request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    try:
        result = await db.donations.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": payload.status}}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")
        
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Donation not found or status already set")
        
    log = ActivityLogDB(
        user_email=user["email"],
        action="rejection" if payload.status == "rejected" else "allocation" if payload.status == "allocated" else "update",
        details=f"Donation {id} status updated to {payload.status}"
    )
    await db.activity_logs.insert_one(log.model_dump())
    return {"message": "Status updated successfully"}

