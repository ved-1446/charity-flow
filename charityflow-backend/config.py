import os
from dotenv import load_dotenv

# Load .env file (checks backend directory first, then current working directory)
_backend_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_backend_env):
    load_dotenv(dotenv_path=_backend_env)
else:
    load_dotenv()

# JWT Secret: must be provided, no fallback allowed
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "FATAL CONFIG ERROR: 'JWT_SECRET' environment variable is missing. "
        "Charity Flow refuses to start without a valid JWT secret."
    )

# MongoDB URI: must be provided, no silent fallback allowed
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError(
        "FATAL CONFIG ERROR: 'MONGO_URI' environment variable is missing. "
        "Charity Flow refuses to start without a MongoDB connection URI."
    )

JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

ADMIN_EMAILS_RAW = os.getenv("ADMIN_EMAILS", "")
ADMIN_EMAILS = [e.strip().lower() for e in ADMIN_EMAILS_RAW.split(",") if e.strip()]

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_DELIVERY_DELAY_SECONDS = int(os.getenv("DEMO_DELIVERY_DELAY_SECONDS", "90"))

# CORS Configuration
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "*")
if CORS_ORIGINS_RAW.strip() == "*":
    CORS_ORIGINS = ["*"]
    CORS_ALLOW_CREDENTIALS = False
else:
    CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]
    CORS_ALLOW_CREDENTIALS = True

# Server Port
PORT = int(os.getenv("PORT", "8000"))

# Proxy Trust: when true, rate limiter respects X-Forwarded-For first IP
TRUST_PROXY = os.getenv("TRUST_PROXY", "false").lower() == "true"

# Optional Cloudinary Storage: if configured, uploads save to Cloudinary; otherwise local /uploads
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "").strip()

# Seed Passwords
SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD")
SEED_DONOR_PASSWORD = os.getenv("SEED_DONOR_PASSWORD")

