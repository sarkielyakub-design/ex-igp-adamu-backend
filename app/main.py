from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import Base, engine

# Import models BEFORE create_all()
from app.models.user import User
from app.models.volunteer import Volunteer

# Create tables
Base.metadata.create_all(bind=engine)

# Create default admin
from app.db.init_admin import create_default_admin
create_default_admin()

# Import routers
from app.api.routes.auth import router as auth_router
from app.api.routes.volunteer import router as volunteer_router
from app.api.routes.admin import router as admin_router

app = FastAPI(
    title="EX IGP Volunteer Registration API",
    version="1.0.0"
)

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://ex-igp-frontend-vaak.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# STATIC FILES
# =========================
app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)

# =========================
# ROUTERS
# =========================
app.include_router(auth_router)
app.include_router(volunteer_router)
app.include_router(admin_router)

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {
        "success": True,
        "message": "EX IGP Volunteer Registration API Running"
    }

# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }