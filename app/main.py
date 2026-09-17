from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import Base, engine


# ============================================================
# PROJECT PATHS
# ============================================================

# main.py:
# /app/app/main.py
#
# APP_DIR:
# /app/app
#
# This matches the location where your current upload generator
# is creating:
# /app/app/uploads/
# ============================================================

APP_DIR = Path(__file__).resolve().parent

UPLOADS_DIR = APP_DIR / "uploads"
CARDS_DIR = UPLOADS_DIR / "cards"
PASSPORTS_DIR = UPLOADS_DIR / "passports"
ASSETS_DIR = APP_DIR / "assets"


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
CARDS_DIR.mkdir(parents=True, exist_ok=True)
PASSPORTS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# IMPORT MODELS BEFORE create_all()
# ============================================================

from app.models.user import User
from app.models.volunteer import Volunteer
from app.models.polling_unit import PollingUnit


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# CREATE DEFAULT ADMIN
# ============================================================

from app.db.init_admin import create_default_admin

create_default_admin()


# ============================================================
# IMPORT ROUTERS
# ============================================================

from app.api.routes.auth import router as auth_router
from app.api.routes.volunteer import router as volunteer_router
from app.api.routes.admin import router as admin_router
from app.api.routes.polling_units import router as polling_units_router


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="EX IGP Volunteer Registration API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ex-igp-frontend.vercel.app",
        "https://ex-igp-frontend-vaak.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STATIC FILES
# ============================================================
#
# Files physically stored at:
#
# /app/app/uploads/
#
# are publicly available as:
#
# /uploads/
#
# Example:
#
# /app/app/uploads/passports/EIAYV-NS-000001.jpeg
#
# becomes:
#
# /uploads/passports/EIAYV-NS-000001.jpeg
#
# And:
#
# /app/app/uploads/cards/EIAYV-NS-000011-membership-card.pdf
#
# becomes:
#
# /uploads/cards/EIAYV-NS-000011-membership-card.pdf
# ============================================================

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_DIR)),
    name="uploads",
)


# ============================================================
# ROUTERS
# ============================================================

# Authentication
app.include_router(auth_router)

# Public volunteer registration
app.include_router(volunteer_router)

# Public polling-unit lookup
app.include_router(polling_units_router)

# Protected admin dashboard/API
app.include_router(admin_router)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "success": True,
        "message": "EX IGP Volunteer Registration API Running",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }