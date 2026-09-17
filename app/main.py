from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db.session import Base, engine


# ============================================================
# PROJECT PATHS
# ============================================================

APP_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = APP_DIR / "uploads"

CARDS_DIR = UPLOADS_DIR / "cards"
PASSPORTS_DIR = UPLOADS_DIR / "passports"
QR_DIR = UPLOADS_DIR / "qr"
ASSETS_DIR = APP_DIR / "assets"


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

for directory in (
    UPLOADS_DIR,
    CARDS_DIR,
    PASSPORTS_DIR,
    QR_DIR,
    ASSETS_DIR,
):
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# IMPORT MODELS
# ============================================================

from app.models.user import User
from app.models.volunteer import Volunteer
from app.models.polling_unit import PollingUnit


# ============================================================
# DATABASE TABLES
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# DEFAULT ADMIN
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

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_DIR)),
    name="uploads",
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(auth_router)
app.include_router(volunteer_router)
app.include_router(polling_units_router)
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