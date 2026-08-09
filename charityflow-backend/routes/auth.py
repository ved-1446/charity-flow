import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status, Request
from jose import jwt
from passlib.hash import bcrypt
from models.user import UserCreate, UserDB
from models.activity_log import ActivityLogDB

router = APIRouter(prefix="/auth", tags=["auth"])

def create_access_token(data: dict):
    to_encode = data.copy()
    expire_hours = int(os.getenv("JWT_EXPIRE_HOURS", "8"))
    expire = datetime.utcnow() + timedelta(hours=expire_hours)
    to_encode.update({"exp": expire})
    secret_key = os.getenv("JWT_SECRET", "charityflow_secret_key_change_in_production")
    return jwt.encode(to_encode, secret_key, algorithm="HS256")

@router.post("/register")
async def register(user: UserCreate, request: Request):
    db = request.app.state.db
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already registered")
        
    admin_emails_str = os.getenv("ADMIN_EMAILS", "")
    admin_emails = [e.strip() for e in admin_emails_str.split(",") if e.strip()]
    
    role = "admin" if user.email in admin_emails else "donor"
    
    hashed_password = bcrypt.hash(user.password)
    
    new_user = UserDB(
        email=user.email,
        password_hash=hashed_password,
        role=role,
        status="active"
    )
    
    result = await db.users.insert_one(new_user.model_dump())
    
    return {"message": "User registered successfully", "role": role}

@router.post("/login")
async def login(user: UserCreate, request: Request):
    db = request.app.state.db
    
    db_user = await db.users.find_one({"email": user.email})
    if not db_user or not bcrypt.verify(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    role = db_user["role"]
    token = create_access_token({"email": user.email, "role": role})
    
    log_entry = ActivityLogDB(
        user_email=user.email,
        action="login",
        details="User logged in successfully"
    )
    await db.activity_logs.insert_one(log_entry.model_dump())
    
    return {"token": token, "role": role, "email": user.email}
