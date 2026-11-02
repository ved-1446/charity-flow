import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from middleware.auth import get_current_user
from middleware.admin_only import admin_only
from models.donation import DonationDB
from models.activity_log import ActivityLogDB
from bson import ObjectId
from pydantic import BaseModel

router = APIRouter(tags=["donations"])

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_COUNT = 5

@router.post("/donate")
async def create_donation(
    request: Request,
    location: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    donorEmail: Optional[str] = Form(None),
    photos: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user)
):
    db = request.app.state.db
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    saved_photos = []

    if len(photos) > MAX_IMAGE_COUNT:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGE_COUNT} files allowed")

    for photo in photos:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTS:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {ext}. Only JPG, PNG, WEBP allowed")
        
        photo.file.seek(0, os.SEEK_END)
        size = photo.file.tell()
        photo.file.seek(0)
        if size > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="Each photo must be smaller than 5 MB")

        new_filename = f"{uuid.uuid4()}{ext}"
        filepath = os.path.join(upload_dir, new_filename)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        saved_photos.append(f"uploads/{new_filename}")
        
    actual_donor_email = user.get("email") or donorEmail or ""
    donation = DonationDB(
        donor_email=actual_donor_email,
        location=location,
        category=category,
        description=description,
        photos=saved_photos,
        status="pending"
    )
    
    result = await db.donations.insert_one(donation.model_dump())
    donation_id = str(result.inserted_id)
    
    log = ActivityLogDB(
        user_email=actual_donor_email,
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
        if "created_at" in document and hasattr(document["created_at"], "isoformat"):
            document["created_at"] = document["created_at"].isoformat()
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
    if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
        doc["created_at"] = doc["created_at"].isoformat()
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

