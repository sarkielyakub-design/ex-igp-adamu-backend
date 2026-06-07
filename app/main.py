from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import Base, engine

# Import ALL models before create_all()
from app.models.user import User
from app.models.volunteer import Volunteer

# Import init admin
from app.db.init_admin import create_default_admin

# Create database tables
Base.metadata.create_all(bind=engine)

# Create default admin automatically
create_default_admin()

# Routes
from app.api.routes.volunteer import router as volunteer_router
from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router

app = FastAPI(
    title="EX IGP Volunteer Registration API",
    version="1.0.0"
)

# =========================
# CORS CONFIGURATION
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)

# Routers
app.include_router(volunteer_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {
        "success": True,
        "message": "EX IGP Volunteer Registration API Running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }