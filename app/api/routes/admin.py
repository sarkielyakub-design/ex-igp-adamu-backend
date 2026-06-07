from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import os

from app.core.dependencies import get_current_admin
from app.db.session import get_db
from app.models.volunteer import Volunteer
from app.utils.excel_export import generate_volunteers_excel

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Dashboard"],
    dependencies=[Depends(get_current_admin)]
)

# =====================================
# REGISTRATION TOGGLE
# =====================================
registration_open = True

@router.get("/registration-status")
def get_registration_status():
    return {
        "open": registration_open
    }

@router.post("/registration-status/toggle")
def toggle_registration_status():
    global registration_open
    registration_open = not registration_open
    return {
        "open": registration_open,
        "message": f"Registration is now {'open' if registration_open else 'closed'}"
    }

# =====================================
# DASHBOARD SUMMARY
# =====================================
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total = db.query(Volunteer).count()
    male = (
        db.query(Volunteer)
        .filter(Volunteer.gender.ilike("male"))
        .count()
    )
    female = (
        db.query(Volunteer)
        .filter(Volunteer.gender.ilike("female"))
        .count()
    )
    employed = (
        db.query(Volunteer)
        .filter(Volunteer.employment_status.ilike("employed"))
        .count()
    )
    unemployed = (
        db.query(Volunteer)
        .filter(Volunteer.employment_status.ilike("unemployed"))
        .count()
    )
    youth_members = (
        db.query(Volunteer)
        .filter(Volunteer.youth_org_member == True)
        .count()
    )
    physically_challenged = (
        db.query(Volunteer)
        .filter(Volunteer.physically_challenged == True)
        .count()
    )
    return {
        "total_volunteers": total,
        "male": male,
        "female": female,
        "employed": employed,
        "unemployed": unemployed,
        "youth_members": youth_members,
        "physically_challenged": physically_challenged
    }

# =====================================
# ALL VOLUNTEERS
# =====================================
@router.get("/volunteers")
def all_volunteers(
    db: Session = Depends(get_db),
    limit: Optional[int] = None,
    sort: Optional[str] = None
):
    query = db.query(Volunteer)
    if sort:
        try:
            field, order = sort.split(":")
            if hasattr(Volunteer, field):
                column = getattr(Volunteer, field)
                if order.lower() == "desc":
                    query = query.order_by(column.desc())
                else:
                    query = query.order_by(column.asc())
        except Exception:
            query = query.order_by(Volunteer.id.desc())
    else:
        query = query.order_by(Volunteer.id.desc())
    if limit:
        query = query.limit(limit)
    volunteers = query.all()
    return {
        "count": len(volunteers),
        "data": volunteers
    }

# =====================================
# RECENT VOLUNTEERS
# =====================================
@router.get("/volunteers/recent")
def recent_volunteers(db: Session = Depends(get_db)):
    volunteers = (
        db.query(Volunteer)
        .order_by(Volunteer.id.desc())
        .limit(5)
        .all()
    )
    return volunteers

# =====================================
# SINGLE VOLUNTEER
# =====================================
@router.get("/volunteer/{volunteer_id}")
def volunteer_details(volunteer_id: int, db: Session = Depends(get_db)):
    volunteer = (
        db.query(Volunteer)
        .filter(Volunteer.id == volunteer_id)
        .first()
    )
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    return volunteer

# =====================================
# DELETE VOLUNTEER
# =====================================
@router.delete("/volunteer/{volunteer_id}")
def delete_volunteer(volunteer_id: int, db: Session = Depends(get_db)):
    volunteer = (
        db.query(Volunteer)
        .filter(Volunteer.id == volunteer_id)
        .first()
    )
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    for file_path in [
        volunteer.passport,       # note: ensure this matches your model field name
        volunteer.qr_code,
        volunteer.id_card
    ]:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    db.delete(volunteer)
    db.commit()
    return {
        "success": True,
        "message": "Volunteer deleted"
    }

# =====================================
# SEARCH VOLUNTEERS
# =====================================
@router.get("/search")
def search_volunteers(keyword: str, db: Session = Depends(get_db)):
    volunteers = (
        db.query(Volunteer)
        .filter(
            Volunteer.name.ilike(f"%{keyword}%") |
            Volunteer.phone.ilike(f"%{keyword}%") |
            Volunteer.registration_no.ilike(f"%{keyword}%")
        )
        .all()
    )
    return volunteers

# =====================================
# MEMBERSHIP CARD DOWNLOAD
# =====================================
@router.get("/membership-card/{registration_no}")
def download_membership_card(registration_no: str, db: Session = Depends(get_db)):
    volunteer = (
        db.query(Volunteer)
        .filter(Volunteer.registration_no == registration_no)
        .first()
    )
    if not volunteer:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    if not volunteer.id_card:
        raise HTTPException(status_code=404, detail="Membership card not found")
    return FileResponse(
        volunteer.id_card,
        media_type="application/pdf",
        filename=f"{registration_no}-membership-card.pdf"
    )

# =====================================
# CURRENT ADMIN
# =====================================
@router.get("/me")
def current_admin(current_user: dict = Depends(get_current_admin)):
    return {
        "username": current_user.get("sub"),
        "role": current_user.get("role")
    }

# =====================================
# EXPORT EXCEL
# =====================================
@router.get("/export/excel")
def export_excel(db: Session = Depends(get_db)):
    volunteers = (
        db.query(Volunteer)
        .order_by(Volunteer.id.desc())
        .all()
    )
    file_path = generate_volunteers_excel(volunteers)
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(file_path)
    )

# =====================================
# LGA ANALYTICS
# =====================================
@router.get("/analytics/lga")
def lga_analytics(db: Session = Depends(get_db)):
    results = (
        db.query(
            Volunteer.lga,
            func.count(Volunteer.id)
        )
        .group_by(Volunteer.lga)
        .all()
    )
    return [
        {"lga": lga, "count": count}
        for lga, count in results
    ]

# =====================================
# GENDER ANALYTICS
# =====================================
@router.get("/analytics/gender")
def gender_analytics(db: Session = Depends(get_db)):
    male = (
        db.query(Volunteer)
        .filter(Volunteer.gender.ilike("male"))
        .count()
    )
    female = (
        db.query(Volunteer)
        .filter(Volunteer.gender.ilike("female"))
        .count()
    )
    return {
        "male": male,
        "female": female
    }

# =====================================
# NOTIFICATIONS
# =====================================
@router.get("/notifications")
def notifications():
    return []