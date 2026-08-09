import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global database client
mongodb_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongodb_client
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/charityflow")
    mongodb_client = AsyncIOMotorClient(mongo_uri)
    app.state.db = mongodb_client.get_default_database()
    print("Connected to MongoDB")
    yield
    mongodb_client.close()
    print("Disconnected from MongoDB")

app = FastAPI(title="Charity Flow API", lifespan=lifespan)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)