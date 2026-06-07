from fastapi import (
    APIRouter,
    Depends,
    Form,
    File,
    UploadFile,
    HTTPException
)
from fastapi.responses import FileResponse
from openpyxl import Workbook
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle
)
from reportlab.lib import colors
from sqlalchemy.orm import Session
import os
import uuid
import qrcode
from datetime import datetime
from fastapi.responses import FileResponse
from app.db.session import get_db
from app.models.volunteer import Volunteer
from app.services.registration_service import generate_registration_no
from app.utils.membership_card_generator import (
    generate_membership_card
)

router = APIRouter(
    prefix="/api/volunteers",
    tags=["Volunteers"]
)

@router.post("/register")
async def register(
    name: str = Form(...),
    phone: str = Form(...),
    gender: str = Form(...),
    age: int = Form(...),
    lga: str = Form(...),
    ward: str = Form(...),
    unit: str = Form(...),
    highest_qualification: str = Form(...),
    additional_qualification: str = Form(None),
    specialization: str = Form(None),
    employment_status: str = Form(...),
    physically_challenged: bool = Form(False),
    youth_org_member: bool = Form(False),
    organization_name: str = Form(None),
    position: str = Form(None),
    expectation: str = Form(None),
    passport: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:

        os.makedirs("uploads/passports", exist_ok=True)
        os.makedirs("uploads/qr", exist_ok=True)
        os.makedirs("uploads/cards", exist_ok=True)

        registration_no = generate_registration_no(db)

        # Save Passport
        ext = passport.filename.split(".")[-1]
        passport_filename = f"{registration_no}.{ext}"

        passport_path = (
            f"uploads/passports/{passport_filename}"
        )

        with open(passport_path, "wb") as buffer:
            buffer.write(await passport.read())

        # Generate QR Code
        qr_path = f"uploads/qr/{registration_no}.png"

        qr = qrcode.make(
            registration_no
        )

        qr.save(qr_path)

        # Save Volunteer
        volunteer = Volunteer(
            registration_no=registration_no,

            passport=passport_path,
            qr_code=qr_path,

            name=name,
            phone=phone,
            gender=gender,
            age=age,

            lga=lga,
            ward=ward,
            unit=unit,

            highest_qualification=highest_qualification,
            additional_qualification=additional_qualification,

            specialization=specialization,

            employment_status=employment_status,

            physically_challenged=physically_challenged,

            youth_org_member=youth_org_member,

            organization_name=organization_name,
            position=position,

            expectation=expectation
        )

        db.add(volunteer)
        db.commit()
        db.refresh(volunteer)

        # Generate Membership Card
        membership_card_path = generate_membership_card(
            volunteer,
            qr_path
        )

        # Save generated card path to the volunteer record (use id_card field)
        volunteer.id_card = membership_card_path

        db.commit()

        return {
            "success": True,
            "message": "Registration successful",
            "registration_no": registration_no,
            "volunteer_id": volunteer.id,
            "passport": passport_path,
            "qr_code": qr_path,
            "id_card": membership_card_path
        }

    except Exception as e:
        import traceback

        traceback.print_exc()

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )
@router.get("/")
def get_all_volunteers(db: Session = Depends(get_db)):
    volunteers = db.query(Volunteer).all()
    
    return {
        "count": len(volunteers),
        "data": volunteers
    }

@router.get("/stats/summary")
def statistics(db: Session = Depends(get_db)):
    return {
        "total_volunteers": db.query(Volunteer).count(),
        "male": db.query(Volunteer)
            .filter(Volunteer.gender.ilike("male"))
            .count(),
        "female": db.query(Volunteer)
            .filter(Volunteer.gender.ilike("female"))
            .count(),
        "employed": db.query(Volunteer)
            .filter(Volunteer.employment_status.ilike("employed"))
            .count(),
        "unemployed": db.query(Volunteer)
            .filter(Volunteer.employment_status.ilike("unemployed"))
            .count(),
        "physically_challenged": db.query(Volunteer)
            .filter(Volunteer.physically_challenged == True)
            .count(),
        "youth_org_members": db.query(Volunteer)
            .filter(Volunteer.youth_org_member == True)
            .count()
    }

@router.get("/search/{registration_no}")
def search_volunteer(registration_no: str, db: Session = Depends(get_db)):
    volunteer = (
        db.query(Volunteer)
        .filter(Volunteer.registration_no == registration_no)
        .first()
    )
    
    if not volunteer:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found"
        )
    return volunteer

@router.get("/{volunteer_id}")
def get_volunteer(volunteer_id: int, db: Session = Depends(get_db)):
    volunteer = (
        db.query(Volunteer)
        .filter(Volunteer.id == volunteer_id)
        .first()
    )
    
    if not volunteer:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found"
        )
    return volunteer

@router.delete("/{volunteer_id}")
def delete_volunteer(volunteer_id: int, db: Session = Depends(get_db)):
    volunteer = (
        db.query(Volunteer)
        .filter(Volunteer.id == volunteer_id)
        .first()
    )
    
    if not volunteer:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found"
        )
    db.delete(volunteer)
    db.commit()
    return {
        "success": True,

        "message": "Volunteer deleted successfully"
    }
@router.get("/membership-card/{registration_no}")
def download_membership_card(
    registration_no: str,
    db: Session = Depends(get_db)
):
    volunteer = db.query(
        Volunteer
    ).filter(
        Volunteer.registration_no ==
        registration_no
    ).first()

    return FileResponse(
        volunteer.id_card,
        media_type="application/pdf",
        filename=f"{registration_no}-membership-card.pdf"
    )
@router.get("/export/excel")
def export_excel(
    db: Session = Depends(get_db)
):
    volunteers = db.query(
        Volunteer
    ).all()

    wb = Workbook()

    ws = wb.active
    ws.title = "Volunteers"

    ws.append([
        "Reg No",
        "Name",
        "Phone",
        "Gender",
        "Age",
        "LGA",
        "Ward",
        "Unit",
        "Qualification"
    ])

    for v in volunteers:
        ws.append([
            v.registration_no,
            v.name,
            v.phone,
            v.gender,
            v.age,
            v.lga,
            v.ward,
            v.unit,
            v.highest_qualification
        ])

    path = "uploads/volunteers.xlsx"

    wb.save(path)

    return FileResponse(
        path,
        filename="volunteers.xlsx"
    )
@router.get("/export/pdf")
def export_pdf(
    db: Session = Depends(get_db)
):
    volunteers = db.query(
        Volunteer
    ).all()

    path = "uploads/volunteers.pdf"

    pdf = SimpleDocTemplate(path)

    data = [[
        "Reg No",
        "Name",
        "Phone",
        "LGA"
    ]]

    for v in volunteers:
        data.append([
            v.registration_no,
            v.name,
            v.phone,
            v.lga
        ])

    table = Table(data)

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.green
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                1,
                colors.black
            ),
        ])
    )

    pdf.build([table])

    return FileResponse(
        path,
        filename="volunteers.pdf"
    )