import os
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request, status
from middleware.auth import get_current_user
from middleware.admin_only import admin_only
from models.donation import DonationDB
from models.activity_log import ActivityLogDB
from bson import ObjectId
from pydantic import BaseModel
from utils.serializers import serialize_date
from config import CLOUDINARY_URL

logger = logging.getLogger("charityflow")

if CLOUDINARY_URL:
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(cloudinary_url=CLOUDINARY_URL)
        logger.info("Cloudinary photo storage enabled")
    except Exception as e:
        logger.warning("Failed to configure Cloudinary: %s", e)

router = APIRouter(tags=["donations"])

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_IMAGE_COUNT = 5

def detect_image_type(data: bytes) -> Optional[str]:
    """
    Inspects real magic bytes (file signature) of image data.
    Returns extension string ('.jpg', '.png', '.webp') or None if invalid.
    """
    if len(data) < 12:
        return None
    # JPEG/JPG: FF D8 FF
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    # WEBP: RIFF....WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None

@router.post("/donate")
async def create_donation(
    request: Request,
    location: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    photos: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user)
):
    db = request.app.state.db
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    saved_photos = []

    if not photos or len(photos) == 0:
        raise HTTPException(status_code=400, detail="At least one photo is required")

    if len(photos) > MAX_IMAGE_COUNT:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGE_COUNT} files allowed")

    for photo in photos:
        content = await photo.read()
        
        # Check size
        if len(content) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="Each photo must be smaller than 5 MB")
        
        # Check magic bytes
        ext = detect_image_type(content)
        if not ext:
            raise HTTPException(
                status_code=400,
                detail="Invalid file signature. Only real JPG, PNG, and WEBP image files are allowed."
            )

        if CLOUDINARY_URL:
            try:
                import cloudinary.uploader
                upload_res = cloudinary.uploader.upload(
                    content,
                    folder="charityflow_donations",
                    resource_type="image"
                )
                cloud_url = upload_res.get("secure_url") or upload_res.get("url")
                if cloud_url:
                    saved_photos.append(cloud_url)
                else:
                    raise ValueError("Cloudinary upload did not return a valid URL")
            except Exception as e:
                logger.error("Cloudinary upload failed: %s; falling back to local file storage", e)
                new_filename = f"{uuid.uuid4()}{ext}"
                filepath = os.path.join(upload_dir, new_filename)
                with open(filepath, "wb") as buffer:
                    buffer.write(content)
                saved_photos.append(f"uploads/{new_filename}")
        else:
            new_filename = f"{uuid.uuid4()}{ext}"
            filepath = os.path.join(upload_dir, new_filename)
            with open(filepath, "wb") as buffer:
                buffer.write(content)
            saved_photos.append(f"uploads/{new_filename}")

    # Use email directly from authenticated user token
    donor_email = user["email"]

    donation = DonationDB(
        donor_email=donor_email,
        location=location,
        category=category,
        description=description,
        photos=saved_photos,
        status="pending"
    )

    result = await db.donations.insert_one(donation.model_dump())
    donation_id = str(result.inserted_id)

    log = ActivityLogDB(
        user_email=donor_email,
        action="donation",
        details=f"New donation submitted with {len(saved_photos)} photos"
    )
    await db.activity_logs.insert_one(log.model_dump())

    return {"message": "Donation submitted successfully", "donation_id": donation_id}

@router.get("/donations")
async def get_donations(request: Request, user: dict = Depends(admin_only)):
    db = request.app.state.db
    cursor = db.donations.find().sort("created_at", -1)
    donations = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        if "created_at" in document:
            document["created_at"] = serialize_date(document["created_at"])
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

    # Only admin or the donor who owns the donation can access
    if user.get("role") != "admin" and doc.get("donor_email") != user.get("email"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this donation"
        )

    doc["_id"] = str(doc["_id"])
    if "created_at" in doc:
        doc["created_at"] = serialize_date(doc["created_at"])
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
