from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, status, Request
from jose import jwt
from passlib.hash import bcrypt
from config import JWT_SECRET, JWT_EXPIRE_HOURS, ADMIN_EMAILS
from models.user import UserCreate, UserDB
from models.activity_log import ActivityLogDB
from utils.rate_limiter import rate_limit_login, rate_limit_register

router = APIRouter(prefix="/auth", tags=["auth"])

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")

@router.post("/register", dependencies=[Depends(rate_limit_register)])
async def register(user: UserCreate, request: Request):
    db = request.app.state.db
    email = user.email.strip().lower()

    # Check if user already exists
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered"
        )

    # Check admin role condition: registration must never create an admin if that admin email already exists
    is_admin_email = email in ADMIN_EMAILS
    if is_admin_email:
        existing_admin = await db.users.find_one({"email": email, "role": "admin"})
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin user with this email already exists"
            )

    role = "admin" if is_admin_email else "donor"
    hashed_password = bcrypt.hash(user.password)

    new_user = UserDB(
        email=email,
        password_hash=hashed_password,
        role=role,
        status="active"
    )

    await db.users.insert_one(new_user.model_dump())

    return {"message": "User registered successfully", "role": role}

@router.post("/login", dependencies=[Depends(rate_limit_login)])
async def login(user: UserCreate, request: Request):
    db = request.app.state.db
    email = user.email.strip().lower()

    db_user = await db.users.find_one({"email": email})
    if not db_user or not bcrypt.verify(user.password, db_user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    role = db_user.get("role", "donor")
    token = create_access_token({"email": email, "role": role})

    log_entry = ActivityLogDB(
        user_email=email,
        action="login",
        details="User logged in successfully"
    )
    await db.activity_logs.insert_one(log_entry.model_dump())

    return {"token": token, "role": role, "email": email}
