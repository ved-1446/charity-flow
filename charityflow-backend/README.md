# Charity Flow — Backend Service

This directory contains the Python FastAPI backend service for the Charity Flow platform.

For full project documentation, architectural diagrams, screenshots, local setup, endpoint references, and deployment guides, please see the primary root README:

👉 **[Root Platform Documentation](../README.md)**

---

## Quick Reference Commands

### Start Backend Locally
```powershell
# From charityflow-backend directory
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

### Seed MongoDB Database
```powershell
python -m seed.seed_all
```

### Run Integration Smoke Tests
```powershell
python tests/smoke_test.py http://127.0.0.1:8000
```
