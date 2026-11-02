import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient

# Load shared config (fails fast if JWT_SECRET or MONGO_URI missing)
from config import MONGO_URI, CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, PORT
from db_indexes import create_indexes

logger = logging.getLogger("charityflow")

# Global database client
mongodb_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongodb_client
    mongodb_client = AsyncIOMotorClient(MONGO_URI)
    app.state.db = mongodb_client.get_default_database()
    logger.info("Connected to MongoDB")

    # Create database indexes safely and idempotently
    await create_indexes(app.state.db)

    yield

    mongodb_client.close()
    logger.info("Disconnected from MongoDB")

app = FastAPI(title="Charity Flow API", lifespan=lifespan)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static files directory for uploads
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
async def root():
    return {"message": "Welcome to Charity Flow API"}

@app.get("/health")
async def health_check():
    global mongodb_client
    try:
        if mongodb_client is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "error", "db": "down"}
            )
        # Ping MongoDB
        await mongodb_client.admin.command("ping")
        return {"status": "ok", "db": "up"}
    except Exception as e:
        logger.error("Health check ping failed: %s", e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "db": "down"}
        )

from routes.auth import router as auth_router
from routes.donations import router as donations_router
from routes.admin import router as admin_router
from routes.logistics import router as logistics_router
from routes.contact import router as contact_router
from routes.reports import router as reports_router
from routes import myaccount

app.include_router(auth_router)
app.include_router(myaccount.router)
app.include_router(donations_router)
app.include_router(admin_router)
app.include_router(logistics_router)
app.include_router(contact_router)
app.include_router(reports_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
