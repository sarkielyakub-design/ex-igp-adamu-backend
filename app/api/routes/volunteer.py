from fastapi import (
    APIRouter,
    Depends,
    Form,
    File,
    UploadFile,
    HTTPException,
)

from fastapi.responses import FileResponse

from openpyxl import Workbook

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
)

from reportlab.lib import colors

from sqlalchemy import func
from sqlalchemy.orm import Session

import os
from io import BytesIO
from pathlib import Path

import qrcode
from PIL import Image

from app.db.session import get_db

from app.models.volunteer import Volunteer
from app.models.polling_unit import PollingUnit

from app.services.registration_service import (
    generate_registration_no,
)

from app.utils.membership_card_generator import (
    generate_membership_card,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/volunteers",
    tags=["Volunteers"],
)


# ============================================================
# CONSTANTS
# ============================================================

NASARAWA_STATE_CODE = "25"
DEFAULT_REGISTRATION_TARGET = 30

# ------------------------------------------------------------------
# Filesystem / upload paths
# volunteer.py lives at: app/api/routes/volunteer.py
# Therefore parents[1] resolves to the FastAPI package directory:
# /app/app on Railway.
# ------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parents[1]
UPLOADS_DIR = APP_DIR / "uploads"

PASSPORTS_DIR = UPLOADS_DIR / "passports"
QR_DIR = UPLOADS_DIR / "qr"
CARDS_DIR = UPLOADS_DIR / "cards"

for directory in (PASSPORTS_DIR, QR_DIR, CARDS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def _web_upload_url(path: str | Path | None) -> str | None:
    """Convert an upload filesystem path to a frontend /uploads URL."""
    if not path:
        return None

    value = str(path).replace("\\", "/")
    marker = "/uploads/"

    if marker in value:
        return value[value.index(marker):]

    if value.startswith("uploads/"):
        return f"/{value}"

    if value.startswith("/uploads/"):
        return value

    return value


def _upload_filesystem_path(path: str | Path | None) -> Path | None:
    """Resolve stored upload paths to an absolute filesystem path."""
    if not path:
        return None

    value = str(path).replace("\\", "/")

    # Absolute path already points to the file.
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate

    # Stored application-relative path, e.g. uploads/cards/file.pdf.
    if value.startswith("uploads/"):
        return APP_DIR / value

    # Stored web path, e.g. /uploads/cards/file.pdf.
    if value.startswith("/uploads/"):
        return APP_DIR / value.lstrip("/")

    # Legacy relative upload path fallback.
    return APP_DIR / value


def _stored_upload_path(path: str | Path) -> str:
    """Store upload paths in the database using a stable relative format."""
    value = str(path).replace("\\", "/")
    marker = "/uploads/"

    if marker in value:
        return "uploads/" + value.split(marker, 1)[1]

    if value.startswith("/uploads/"):
        return value.lstrip("/")

    if value.startswith("uploads/"):
        return value

    return value


def _serialize_volunteer(volunteer):
    """Return a JSON-safe volunteer payload with browser-safe upload URLs."""
    data = {}

    for attribute in volunteer.__mapper__.column_attrs:
        key = attribute.key
        value = getattr(volunteer, key)

        if key in {"passport", "qr_code", "id_card"}:
            value = _web_upload_url(value)

        data[key] = value

    return data


def _serialize_volunteers(volunteers):
    return [_serialize_volunteer(v) for v in volunteers]


# ============================================================
# REGISTER VOLUNTEER
# ============================================================

@router.post("/register")
async def register(
    # --------------------------------------------------------
    # PERSONAL INFORMATION
    # --------------------------------------------------------

    name: str = Form(...),
    phone: str = Form(...),
    gender: str = Form(...),
    age: int = Form(...),

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------
    # polling_unit_id is the authoritative location.
    #
    # The frontend may still send lga/ward/unit for compatibility,
    # but we do NOT trust those values. They are overwritten from
    # the selected PollingUnit record below.
    # --------------------------------------------------------

    lga: str = Form(None),
    ward: str = Form(None),
    unit: str = Form(None),

    polling_unit_id: int = Form(...),

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    highest_qualification: str = Form(...),
    additional_qualification: str = Form(None),
    specialization: str = Form(None),

    # --------------------------------------------------------
    # EMPLOYMENT
    # --------------------------------------------------------

    employment_status: str = Form(...),

    # --------------------------------------------------------
    # OTHER
    # --------------------------------------------------------

    physically_challenged: bool = Form(False),

    youth_org_member: bool = Form(False),

    organization_name: str = Form(None),

    position: str = Form(None),

    expectation: str = Form(None),

    # --------------------------------------------------------
    # PASSPORT
    # --------------------------------------------------------

    passport: UploadFile = File(...),

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    db: Session = Depends(get_db),
):
    passport_path = None
    qr_path = None
    membership_card_path = None

    try:

        # ====================================================
        # BASIC VALIDATION
        # ====================================================

        name = name.strip()
        phone = phone.strip()

        if not name:
            raise HTTPException(
                status_code=400,
                detail="Name is required",
            )

        if not phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number is required",
            )

        if age < 1 or age > 120:
            raise HTTPException(
                status_code=400,
                detail="Invalid age",
            )

        if not passport.filename:
            raise HTTPException(
                status_code=400,
                detail="Passport image is required",
            )

        # ====================================================
        # GET AND LOCK POLLING UNIT
        # ====================================================
        #
        # The row is locked so two users cannot simultaneously
        # register into the same final available slot.
        # ====================================================

        polling_unit = (
            db.query(PollingUnit)
            .filter(
                PollingUnit.id == polling_unit_id,
                PollingUnit.state_code == NASARAWA_STATE_CODE,
            )
            .with_for_update()
            .first()
        )

        if not polling_unit:
            raise HTTPException(
                status_code=404,
                detail="Polling unit not found",
            )

        # ====================================================
        # GET REGISTRATION TARGET
        # ====================================================

        target = (
            polling_unit.registration_target
            or DEFAULT_REGISTRATION_TARGET
        )

        # ====================================================
        # COUNT ACTUAL VOLUNTEERS
        # ====================================================
        #
        # The Volunteer table is the source of the actual number
        # of registrations assigned to this polling unit.
        # ====================================================

        registration_count = (
            db.query(func.count(Volunteer.id))
            .filter(
                Volunteer.polling_unit_id == polling_unit.id
            )
            .scalar()
        )

        registration_count = int(
            registration_count or 0
        )

        # ====================================================
        # SYNCHRONIZE STORED POLLING UNIT COUNT
        # ====================================================

        polling_unit.registered_count = registration_count

        # ====================================================
        # CHECK CAPACITY
        # ====================================================

        if registration_count >= target:

            polling_unit.status = "FULL"

            db.commit()

            raise HTTPException(
                status_code=409,
                detail=(
                    f"This polling unit has reached "
                    f"its registration target of {target}."
                ),
            )

        # ====================================================
        # ENSURE STATUS IS OPEN
        # ====================================================

        polling_unit.status = "OPEN"

        # ====================================================
        # USE ACTUAL LOCATION FROM POLLING UNIT
        # ====================================================
        #
        # Never trust the location text sent by the browser.
        # The selected polling unit determines the location.
        # ====================================================

        lga = polling_unit.lga_name
        ward = polling_unit.ward_name
        unit = polling_unit.pu_name

        # ====================================================
        # ENSURE UPLOAD DIRECTORIES EXIST
        # ====================================================

        PASSPORTS_DIR.mkdir(parents=True, exist_ok=True)
        QR_DIR.mkdir(parents=True, exist_ok=True)
        CARDS_DIR.mkdir(parents=True, exist_ok=True)

        # ====================================================
        # GENERATE REGISTRATION NUMBER
        # ====================================================

        registration_no = generate_registration_no(db)

        # ====================================================
        # SAVE PASSPORT / VOLUNTEER PHOTO
        # ====================================================

        original_filename = (passport.filename or "").strip()

        if not original_filename:
            raise HTTPException(
                status_code=400,
                detail="Passport image is required",
            )

        ext = (
            original_filename.rsplit(".", 1)[-1].lower()
            if "." in original_filename
            else "jpg"
        )

        allowed_extensions = {"jpg", "jpeg", "png", "webp", "jfif"}

        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid passport image format. "
                    "Allowed formats: JPG, JPEG, PNG, WEBP, JFIF."
                ),
            )

        passport_filename = f"{registration_no}.{ext}"
        passport_fs_path = PASSPORTS_DIR / passport_filename
        passport_path = _stored_upload_path(passport_fs_path)

        passport_content = await passport.read()

        if not passport_content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded passport image is empty",
            )

        if len(passport_content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Passport image is too large. Maximum size is 10MB.",
            )

        try:
            with Image.open(BytesIO(passport_content)) as image:
                image.verify()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="The uploaded passport is not a valid image.",
            )

        with passport_fs_path.open("wb") as buffer:
            buffer.write(passport_content)

        if not passport_fs_path.exists() or passport_fs_path.stat().st_size == 0:
            raise RuntimeError("Passport image could not be saved.")

        # ====================================================
        # GENERATE QR CODE
        # ====================================================

        qr_fs_path = QR_DIR / f"{registration_no}.png"
        qr_path = _stored_upload_path(qr_fs_path)

        qr = qrcode.make(registration_no)
        qr.save(str(qr_fs_path))

        if not qr_fs_path.exists() or qr_fs_path.stat().st_size == 0:
            raise RuntimeError("QR code could not be generated.")

        # ====================================================
        # CREATE VOLUNTEER
        # ====================================================

        volunteer = Volunteer(

            # ------------------------------------------------
            # Registration
            # ------------------------------------------------

            registration_no=registration_no,

            # ------------------------------------------------
            # Files
            # ------------------------------------------------

            passport=passport_path,
            qr_code=qr_path,

            # ------------------------------------------------
            # Personal information
            # ------------------------------------------------

            name=name,
            phone=phone,
            gender=gender,
            age=age,

            # ------------------------------------------------
            # Location
            # ------------------------------------------------

            lga=lga,
            ward=ward,
            unit=unit,

            polling_unit_id=polling_unit.id,

            # ------------------------------------------------
            # Education
            # ------------------------------------------------

            highest_qualification=(
                highest_qualification
            ),

            additional_qualification=(
                additional_qualification
            ),

            specialization=specialization,

            # ------------------------------------------------
            # Employment
            # ------------------------------------------------

            employment_status=(
                employment_status
            ),

            # ------------------------------------------------
            # Other
            # ------------------------------------------------

            physically_challenged=(
                physically_challenged
            ),

            youth_org_member=(
                youth_org_member
            ),

            organization_name=(
                organization_name
            ),

            position=position,

            expectation=expectation,
        )

        db.add(volunteer)

        # ====================================================
        # FLUSH
        # ====================================================
        #
        # This gives us the volunteer ID without committing yet.
        # ====================================================

        db.flush()

        # ====================================================
        # UPDATE POLLING UNIT COUNT
        # ====================================================

        new_count = registration_count + 1

        polling_unit.registered_count = new_count

        # ====================================================
        # UPDATE POLLING UNIT STATUS
        # ====================================================

        if new_count >= target:
            polling_unit.status = "FULL"
        else:
            polling_unit.status = "OPEN"

        # ====================================================
        # GENERATE MEMBERSHIP CARD BEFORE DATABASE COMMIT
        # ====================================================
        #
        # The volunteer is already flushed, so the card generator can
        # read all volunteer fields and the uploaded photo. The actual
        # filesystem paths are passed to the generator, while the DB
        # stores stable relative paths.
        # ====================================================

        expected_card_fs_path = (
            CARDS_DIR / f"{registration_no}-membership-card.pdf"
        )

        membership_card_generated_path = generate_membership_card(
            volunteer,
            str(qr_fs_path),
        )

        if not membership_card_generated_path:
            raise RuntimeError(
                "Membership card generator returned no file."
            )

        membership_card_path = _stored_upload_path(
            membership_card_generated_path
        )

        card_fs_path = _upload_filesystem_path(
            membership_card_path
        )

        # Some generator versions return a path that is not normalized
        # exactly as expected. Fall back to the deterministic card path.
        if not card_fs_path or not card_fs_path.exists():
            if expected_card_fs_path.exists():
                card_fs_path = expected_card_fs_path
                membership_card_path = _stored_upload_path(
                    expected_card_fs_path
                )
            else:
                raise RuntimeError(
                    "Membership card was generated but the PDF file "
                    "could not be found."
                )

        if card_fs_path.stat().st_size == 0:
            raise RuntimeError("Membership card PDF was generated empty.")

        volunteer.id_card = membership_card_path

        # ====================================================
        # UPDATE POLLING UNIT COUNT
        # ====================================================

        new_count = registration_count + 1
        polling_unit.registered_count = new_count

        if new_count >= target:
            polling_unit.status = "FULL"
        else:
            polling_unit.status = "OPEN"

        # ====================================================
        # FINAL FILE VERIFICATION
        # ====================================================

        for required_file, label in (
            (passport_fs_path, "Passport image"),
            (qr_fs_path, "QR code"),
            (card_fs_path, "Membership card"),
        ):
            if not required_file.exists() or required_file.stat().st_size == 0:
                raise RuntimeError(
                    f"{label} could not be verified before registration commit."
                )

        # ====================================================
        # SINGLE DATABASE COMMIT
        # ====================================================
        #
        # Card generation happens before this commit. Therefore a failed
        # card generation cannot leave behind a database registration.
        # ====================================================

        db.commit()
        db.refresh(volunteer)

        # ====================================================
        # RETURN REGISTRATION RESULT
        # ====================================================

        return {

            "success": True,

            "message": (
                "Registration successful"
            ),

            "notification": {
                "type": "success",
                "title": "Registration Successful",
                "message": (
                    f"{name} has been successfully registered "
                    f"as a volunteer."
                ),
            },

            "registration_no": (
                registration_no
            ),

            "volunteer_id": (
                volunteer.id
            ),

            # ------------------------------------------------
            # Files
            # ------------------------------------------------

            "passport": _web_upload_url(passport_path),

            "qr_code": _web_upload_url(qr_path),

            "id_card": _web_upload_url(membership_card_path),

            # ------------------------------------------------
            # Location
            # ------------------------------------------------

            "location": {

                "lga": (
                    polling_unit.lga_name
                ),

                "lga_code": (
                    polling_unit.lga_code
                ),

                "ward": (
                    polling_unit.ward_name
                ),

                "ward_code": (
                    polling_unit.ward_code
                ),

                "polling_unit": (
                    polling_unit.pu_name
                ),

                "polling_unit_code": (
                    polling_unit.pu_code
                ),

                "full_code": (
                    polling_unit.full_code
                ),

                "location": (
                    polling_unit.pu_location
                ),
            },

            # ------------------------------------------------
            # Polling unit capacity
            # ------------------------------------------------

            "polling_unit_id": (
                polling_unit.id
            ),

            "polling_unit_target": target,

            "polling_unit_registered": (
                new_count
            ),

            "polling_unit_remaining": (
                max(
                    target - new_count,
                    0,
                )
            ),

            "polling_unit_status": (
                polling_unit.status
            ),
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:

        import traceback

        traceback.print_exc()

        db.rollback()

        # ----------------------------------------------------
        # Clean up files created during a failed transaction.
        # ----------------------------------------------------

        cleanup_paths = [
            passport_path,
            qr_path,
            membership_card_path,
        ]

        # The card generator can create the deterministic card file before
        # returning its path. Include it in cleanup if registration fails.
        try:
            if registration_no:
                cleanup_paths.append(
                    CARDS_DIR / f"{registration_no}-membership-card.pdf"
                )
        except Exception:
            pass

        for file_path in cleanup_paths:
            resolved_path = _upload_filesystem_path(file_path)

            if resolved_path and resolved_path.exists():
                try:
                    resolved_path.unlink()
                except OSError:
                    pass

        raise HTTPException(
            status_code=500,
            detail=(
                f"Registration failed: {str(e)}"
            ),
        )


# ============================================================
# GET ALL VOLUNTEERS
# ============================================================

@router.get("/")
def get_all_volunteers(
    db: Session = Depends(get_db),
):

    volunteers = (
        db.query(Volunteer)
        .order_by(
            Volunteer.created_at.desc()
        )
        .all()
    )

    return {
        "count": len(volunteers),
        "data": _serialize_volunteers(volunteers),
    }


# ============================================================
# STATISTICS
# ============================================================

@router.get("/stats/summary")
def statistics(
    db: Session = Depends(get_db),
):

    # ========================================================
    # VOLUNTEER COUNTS
    # ========================================================

    total = (
        db.query(Volunteer)
        .count()
    )

    male = (
        db.query(Volunteer)
        .filter(
            Volunteer.gender.ilike("male")
        )
        .count()
    )

    female = (
        db.query(Volunteer)
        .filter(
            Volunteer.gender.ilike("female")
        )
        .count()
    )

    employed = (
        db.query(Volunteer)
        .filter(
            Volunteer.employment_status.ilike(
                "employed"
            )
        )
        .count()
    )

    unemployed = (
        db.query(Volunteer)
        .filter(
            Volunteer.employment_status.ilike(
                "unemployed"
            )
        )
        .count()
    )

    physically_challenged = (
        db.query(Volunteer)
        .filter(
            Volunteer.physically_challenged.is_(True)
        )
        .count()
    )

    youth_org_members = (
        db.query(Volunteer)
        .filter(
            Volunteer.youth_org_member.is_(True)
        )
        .count()
    )

    # ========================================================
    # POLLING UNIT STATISTICS
    # ========================================================

    total_polling_units = (
        db.query(PollingUnit)
        .filter(
            PollingUnit.state_code
            == NASARAWA_STATE_CODE
        )
        .count()
    )

    full_polling_units = (
        db.query(PollingUnit)
        .filter(
            PollingUnit.state_code
            == NASARAWA_STATE_CODE,
            PollingUnit.status == "FULL",
        )
        .count()
    )

    open_polling_units = (
        db.query(PollingUnit)
        .filter(
            PollingUnit.state_code
            == NASARAWA_STATE_CODE,
            PollingUnit.status == "OPEN",
        )
        .count()
    )

    # ========================================================
    # TOTAL REGISTRATION TARGET
    # ========================================================

    total_target = (
        db.query(
            func.coalesce(
                func.sum(
                    PollingUnit.registration_target
                ),
                0,
            )
        )
        .filter(
            PollingUnit.state_code
            == NASARAWA_STATE_CODE
        )
        .scalar()
    )

    total_target = int(
        total_target or 0
    )

    # ========================================================
    # TOTAL REGISTERED
    # ========================================================
    #
    # Volunteer records represent actual registrations.
    # ========================================================

    total_registered = (
        db.query(Volunteer)
        .join(
            PollingUnit,
            Volunteer.polling_unit_id
            == PollingUnit.id,
        )
        .filter(
            PollingUnit.state_code
            == NASARAWA_STATE_CODE
        )
        .count()
    )

    # ========================================================
    # REMAINING CAPACITY
    # ========================================================

    total_remaining = max(
        total_target - total_registered,
        0,
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "total_volunteers": total,

        "male": male,

        "female": female,

        "employed": employed,

        "unemployed": unemployed,

        "physically_challenged": (
            physically_challenged
        ),

        "youth_org_members": (
            youth_org_members
        ),

        # ----------------------------------------------------
        # Polling units
        # ----------------------------------------------------

        "total_polling_units": (
            total_polling_units
        ),

        "full_polling_units": (
            full_polling_units
        ),

        "open_polling_units": (
            open_polling_units
        ),

        # ----------------------------------------------------
        # Registration target
        # ----------------------------------------------------

        "total_registration_target": (
            total_target
        ),

        "total_registered": (
            total_registered
        ),

        "total_remaining": (
            total_remaining
        ),
    }


# ============================================================
# SEARCH VOLUNTEER BY REGISTRATION NUMBER
# ============================================================

@router.get("/search/{registration_no}")
def search_volunteer(
    registration_no: str,
    db: Session = Depends(get_db),
):

    volunteer = (
        db.query(Volunteer)
        .filter(
            Volunteer.registration_no
            == registration_no
        )
        .first()
    )

    if not volunteer:

        raise HTTPException(
            status_code=404,
            detail="Volunteer not found",
        )

    return _serialize_volunteer(volunteer)


# ============================================================
# GET VOLUNTEER
# ============================================================

@router.get("/{volunteer_id}")
def get_volunteer(
    volunteer_id: int,
    db: Session = Depends(get_db),
):

    volunteer = (
        db.query(Volunteer)
        .filter(
            Volunteer.id == volunteer_id
        )
        .first()
    )

    if not volunteer:

        raise HTTPException(
            status_code=404,
            detail="Volunteer not found",
        )

    return _serialize_volunteer(volunteer)


# ============================================================
# DELETE VOLUNTEER
# ============================================================

@router.delete("/{volunteer_id}")
def delete_volunteer(
    volunteer_id: int,
    db: Session = Depends(get_db),
):

    volunteer = (
        db.query(Volunteer)
        .filter(
            Volunteer.id == volunteer_id
        )
        .first()
    )

    if not volunteer:

        raise HTTPException(
            status_code=404,
            detail="Volunteer not found",
        )

    # ========================================================
    # GET ASSIGNED POLLING UNIT
    # ========================================================

    polling_unit = None

    if volunteer.polling_unit_id:

        polling_unit = (
            db.query(PollingUnit)
            .filter(
                PollingUnit.id
                == volunteer.polling_unit_id
            )
            .with_for_update()
            .first()
        )

    # ========================================================
    # REMOVE UPLOADED FILES
    # ========================================================

    for file_path in (
        volunteer.passport,
        volunteer.qr_code,
        volunteer.id_card,
    ):
        resolved_path = _upload_filesystem_path(file_path)

        if resolved_path and resolved_path.exists():
            try:
                resolved_path.unlink()
            except OSError:
                pass

    # ========================================================
    # DELETE VOLUNTEER
    # ========================================================

    db.delete(volunteer)

    # ========================================================
    # UPDATE POLLING UNIT COUNT
    # ========================================================

    if polling_unit:

        current_count = (
            db.query(Volunteer)
            .filter(
                Volunteer.polling_unit_id
                == polling_unit.id
            )
            .count()
        )

        # The volunteer is still in the session until the
        # transaction is flushed, so subtract one.

        new_count = max(
            current_count - 1,
            0,
        )

        polling_unit.registered_count = (
            new_count
        )

        target = (
            polling_unit.registration_target
            or DEFAULT_REGISTRATION_TARGET
        )

        polling_unit.status = (
            "FULL"
            if new_count >= target
            else "OPEN"
        )

    # ========================================================
    # COMMIT
    # ========================================================

    db.commit()

    return {

        "success": True,

        "message": (
            "Volunteer deleted successfully"
        ),

        "polling_unit": (
            {
                "id": polling_unit.id,

                "registered_count": (
                    polling_unit.registered_count
                ),

                "registration_target": (
                    polling_unit.registration_target
                    or DEFAULT_REGISTRATION_TARGET
                ),

                "remaining": max(
                    (
                        polling_unit.registration_target
                        or DEFAULT_REGISTRATION_TARGET
                    )
                    - (
                        polling_unit.registered_count
                        or 0
                    ),
                    0,
                ),

                "status": polling_unit.status,
            }
            if polling_unit
            else None
        ),
    }


# ============================================================
# DOWNLOAD MEMBERSHIP CARD
# ============================================================

@router.get(
    "/membership-card/{registration_no}"
)
def download_membership_card(
    registration_no: str,
    db: Session = Depends(get_db),
):

    volunteer = (
        db.query(Volunteer)
        .filter(
            Volunteer.registration_no
            == registration_no
        )
        .first()
    )

    if not volunteer:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found",
        )

    card_path = (
        _upload_filesystem_path(volunteer.id_card)
        if volunteer.id_card
        else None
    )

    # --------------------------------------------------------
    # REGENERATE MISSING CARD FOR EXISTING VOLUNTEERS
    # --------------------------------------------------------
    if not card_path or not card_path.exists():
        passport_fs = _upload_filesystem_path(volunteer.passport)

        if not passport_fs or not passport_fs.exists():
            raise HTTPException(
                status_code=404,
                detail="Volunteer passport image file not found.",
            )

        qr_fs = _upload_filesystem_path(volunteer.qr_code)

        if not qr_fs or not qr_fs.exists():
            QR_DIR.mkdir(parents=True, exist_ok=True)
            qr_fs = QR_DIR / f"{registration_no}.png"
            try:
                qr = qrcode.make(registration_no)
                qr.save(str(qr_fs))
            except Exception as exc:
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Could not rebuild volunteer QR code: {exc}",
                )

        try:
            regenerated_path = generate_membership_card(
                volunteer,
                str(qr_fs),
            )

            stored_path = _stored_upload_path(regenerated_path)
            regenerated_fs = _upload_filesystem_path(stored_path)

            if not regenerated_fs or not regenerated_fs.exists():
                fallback = CARDS_DIR / f"{registration_no}-membership-card.pdf"
                if fallback.exists():
                    regenerated_fs = fallback
                    stored_path = _stored_upload_path(fallback)
                else:
                    raise RuntimeError(
                        "Regenerated membership card file was not found."
                    )

            volunteer.id_card = stored_path
            db.commit()
            db.refresh(volunteer)
            card_path = regenerated_fs

        except HTTPException:
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=(
                    "Membership card could not be generated. "
                    f"{exc}"
                ),
            )

    if not card_path or not card_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Membership card file not found.",
        )

    return FileResponse(
        str(card_path),
        media_type="application/pdf",
        filename=f"{registration_no}-membership-card.pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{registration_no}-membership-card.pdf"'
            )
        },
    )


# ============================================================
# EXPORT EXCEL
# ============================================================

@router.get("/export/excel")
def export_excel(
    db: Session = Depends(get_db),
):

    volunteers = (
        db.query(Volunteer)
        .order_by(
            Volunteer.created_at.desc()
        )
        .all()
    )

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOADS_DIR / "volunteers.xlsx"

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

        "Polling Unit ID",

        "Qualification",

        "Employment Status",

        "Organization Member",

        "Created At",
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

            v.polling_unit_id,

            v.highest_qualification,

            v.employment_status,

            v.youth_org_member,

            v.created_at,
        ])

    wb.save(path)

    return FileResponse(
        str(path),
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),

        filename="volunteers.xlsx",
    )


# ============================================================
# EXPORT PDF
# ============================================================

@router.get("/export/pdf")
def export_pdf(
    db: Session = Depends(get_db),
):

    volunteers = (
        db.query(Volunteer)
        .order_by(
            Volunteer.created_at.desc()
        )
        .all()
    )

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOADS_DIR / "volunteers.pdf"

    pdf = SimpleDocTemplate(path)

    data = [[

        "Reg No",

        "Name",

        "Phone",

        "LGA",

        "Ward",

        "Polling Unit",
    ]]

    for v in volunteers:

        data.append([

            v.registration_no,

            v.name,

            v.phone,

            v.lga,

            v.ward,

            v.unit,
        ])

    table = Table(data)

    table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.green,
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white,
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                1,
                colors.black,
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold",
            ),

            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "LEFT",
            ),
        ])
    )

    pdf.build([table])

    return FileResponse(
        str(path),
        media_type="application/pdf",

        filename="volunteers.pdf",
    )