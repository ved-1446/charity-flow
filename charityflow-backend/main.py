import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse, FileResponse, Response
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

@app.get("/api")
async def api_root():
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

# --- Frontend Serving (Single-URL Deployment) ---
# Allowed frontend HTML pages (explicit whitelist)
ALLOWED_HTML_FILES = {
    "login.html",
    "frontend.html",
    "donate.html",
    "contactus.html",
    "ourservices.html",
    "aboutus.html",
    "myaccount.html",
    "admin.html",
    "item-allocation.html",
    "dropoff-tracking.html",
    "manage-users.html",
    "reports-history.html",
}

# Resolve repository root directory (supports both local and Render layouts)
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
if os.path.exists(os.path.join(PARENT_DIR, "login.html")):
    REPO_ROOT = PARENT_DIR
elif os.path.exists(os.path.join(BACKEND_DIR, "login.html")):
    REPO_ROOT = BACKEND_DIR
elif os.path.exists(os.path.join(BACKEND_DIR, "static", "login.html")):
    REPO_ROOT = os.path.join(BACKEND_DIR, "static")
else:
    REPO_ROOT = PARENT_DIR

class SafeFrontendStaticFiles(StaticFiles):
    """
    Serves only frontend HTML pages and assets/.
    Explicitly refuses access to .env, python files, backend sources, tests, and venv.
    """
    async def get_response(self, path: str, scope):
        norm_path = path.replace("\\", "/").strip("/")

        # Security: reject directory traversal, hidden files, .env, python files, or backend/venv folders
        if (
            ".." in norm_path
            or norm_path.startswith(".")
            or ".env" in norm_path
            or norm_path.endswith(".py")
            or norm_path.startswith("charityflow-backend")
            or norm_path.startswith("venv")
            or norm_path.startswith("tests")
        ):
            return Response("Not Found", status_code=404)

        # Serve login.html for root or empty path
        if norm_path == "" or norm_path == "index.html":
            login_path = os.path.join(self.directory, "login.html")
            if os.path.isfile(login_path):
                return FileResponse(login_path)
            return Response("Not Found", status_code=404)

        # Serve explicitly allowed HTML files
        if norm_path in ALLOWED_HTML_FILES:
            return await super().get_response(norm_path, scope)

        # Serve assets directory
        if norm_path.startswith("assets/"):
            return await super().get_response(norm_path, scope)

        # Deny all other files
        return Response("Not Found", status_code=404)

# Explicit root route: "/" must open login.html
@app.get("/")
async def serve_root_login():
    login_path = os.path.join(REPO_ROOT, "login.html")
    if os.path.isfile(login_path):
        return FileResponse(login_path)
    return JSONResponse(status_code=404, content={"detail": "login.html not found"})

# Mount frontend AFTER all API routers, uploads, and health routes
app.mount("/", SafeFrontendStaticFiles(directory=REPO_ROOT), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
