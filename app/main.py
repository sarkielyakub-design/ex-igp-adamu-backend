from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import Base, engine


# ============================================================
# PROJECT PATHS
# ============================================================
# main.py is located at:
#   /app/app/main.py
#
# parent      -> /app/app
# parent.parent -> /app
#
# Therefore BASE_DIR becomes the actual backend project root.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOADS_DIR = BASE_DIR / "uploads"
CARDS_DIR = UPLOADS_DIR / "cards"
ASSETS_DIR = BASE_DIR / "assets"


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
CARDS_DIR.mkdir(parents=True, exist_ok=True)
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
# Public URL:
#
#   /uploads/cards/example.pdf
#
# Maps to:
#
#   /app/uploads/cards/example.pdf
#
# This must match the location where the membership-card
# generator saves generated PDF files.
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