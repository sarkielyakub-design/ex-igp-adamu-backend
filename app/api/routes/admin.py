from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
import os

from app.core.dependencies import get_current_admin
from app.db.session import get_db
from app.models.volunteer import Volunteer
from app.models.polling_unit import PollingUnit
from app.utils.excel_export import generate_volunteers_excel


router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Dashboard"],
    dependencies=[Depends(get_current_admin)],
)


# ============================================================
# REGISTRATION TOGGLE
# ============================================================

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
        "message": (
            f"Registration is now "
            f"{'open' if registration_open else 'closed'}"
        ),
    }


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

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
        .filter(Volunteer.youth_org_member.is_(True))
        .count()
    )

    physically_challenged = (
        db.query(Volunteer)
        .filter(Volunteer.physically_challenged.is_(True))
        .count()
    )

    # Polling Unit statistics
    total_polling_units = db.query(PollingUnit).count()

    full_polling_units = (
        db.query(PollingUnit)
        .filter(PollingUnit.status == "FULL")
        .count()
    )

    open_polling_units = (
        db.query(PollingUnit)
        .filter(PollingUnit.status == "OPEN")
        .count()
    )

    total_registration_target = (
        db.query(
            func.coalesce(
                func.sum(PollingUnit.registration_target),
                0,
            )
        )
        .scalar()
        or 0
    )

    total_registered = (
        db.query(
            func.coalesce(
                func.sum(PollingUnit.registered_count),
                0,
            )
        )
        .scalar()
        or 0
    )

    total_remaining = max(
        total_registration_target - total_registered,
        0,
    )

    return {
        "total_volunteers": total,
        "male": male,
        "female": female,
        "employed": employed,
        "unemployed": unemployed,
        "youth_members": youth_members,
        "physically_challenged": physically_challenged,

        "polling_units": {
            "total": total_polling_units,
            "open": open_polling_units,
            "full": full_polling_units,
            "target": total_registration_target,
            "registered": total_registered,
            "remaining": total_remaining,
        },

        "registration": {
            "open": registration_open,
        },
    }


# ============================================================
# POLLING UNIT SUMMARY
# ============================================================

@router.get("/polling-units/summary")
def polling_units_summary(
    db: Session = Depends(get_db),
):
    total = db.query(PollingUnit).count()

    open_units = (
        db.query(PollingUnit)
        .filter(PollingUnit.status == "OPEN")
        .count()
    )

    full_units = (
        db.query(PollingUnit)
        .filter(PollingUnit.status == "FULL")
        .count()
    )

    target = (
        db.query(
            func.coalesce(
                func.sum(PollingUnit.registration_target),
                0,
            )
        )
        .scalar()
        or 0
    )

    registered = (
        db.query(
            func.coalesce(
                func.sum(PollingUnit.registered_count),
                0,
            )
        )
        .scalar()
        or 0
    )

    remaining = max(target - registered, 0)

    return {
        "total_polling_units": total,
        "open_polling_units": open_units,
        "full_polling_units": full_units,
        "registration_target": target,
        "registered": registered,
        "remaining": remaining,
    }


# ============================================================
# LIST LGAs
# ============================================================

@router.get("/polling-units/lgas")
def list_lgas(
    db: Session = Depends(get_db),
):
    """
    Return all Nasarawa LGAs represented in the polling-unit data.
    """

    rows = (
        db.query(
            PollingUnit.lga_code,
            PollingUnit.lga_name,
            func.count(PollingUnit.id).label("polling_units"),
            func.coalesce(
                func.sum(PollingUnit.registration_target),
                0,
            ).label("target"),
            func.coalesce(
                func.sum(PollingUnit.registered_count),
                0,
            ).label("registered"),
        )
        .group_by(
            PollingUnit.lga_code,
            PollingUnit.lga_name,
        )
        .order_by(PollingUnit.lga_code.asc())
        .all()
    )

    data = []

    for row in rows:
        target = int(row.target or 0)
        registered = int(row.registered or 0)

        data.append({
            "lga_code": row.lga_code,
            "lga_name": row.lga_name,
            "polling_units": row.polling_units,
            "target": target,
            "registered": registered,
            "remaining": max(target - registered, 0),
        })

    return {
        "count": len(data),
        "data": data,
    }


# ============================================================
# LIST WARDS / REGISTRATION AREAS
# ============================================================

@router.get("/polling-units/lgas/{lga_code}/wards")
def list_wards(
    lga_code: str,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            PollingUnit.ward_code,
            PollingUnit.ward_name,
            func.count(PollingUnit.id).label("polling_units"),
            func.coalesce(
                func.sum(PollingUnit.registration_target),
                0,
            ).label("target"),
            func.coalesce(
                func.sum(PollingUnit.registered_count),
                0,
            ).label("registered"),
        )
        .filter(PollingUnit.lga_code == lga_code)
        .group_by(
            PollingUnit.ward_code,
            PollingUnit.ward_name,
        )
        .order_by(PollingUnit.ward_code.asc())
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="LGA not found or has no polling units",
        )

    data = []

    for row in rows:
        target = int(row.target or 0)
        registered = int(row.registered or 0)

        data.append({
            "ward_code": row.ward_code,
            "ward_name": row.ward_name,
            "polling_units": row.polling_units,
            "target": target,
            "registered": registered,
            "remaining": max(target - registered, 0),
        })

    return {
        "lga_code": lga_code,
        "count": len(data),
        "data": data,
    }


# ============================================================
# LIST POLLING UNITS FOR WARD
# ============================================================

@router.get(
    "/polling-units/lgas/{lga_code}/wards/{ward_code}"
)
def list_polling_units(
    lga_code: str,
    ward_code: str,
    db: Session = Depends(get_db),
    status: Optional[str] = Query(
        None,
        description="OPEN or FULL",
    ),
):
    query = (
        db.query(PollingUnit)
        .filter(
            PollingUnit.lga_code == lga_code,
            PollingUnit.ward_code == ward_code,
        )
    )

    if status:
        status = status.upper()

        if status not in ["OPEN", "FULL"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be OPEN or FULL",
            )

        query = query.filter(
            PollingUnit.status == status
        )

    units = (
        query
        .order_by(PollingUnit.pu_code.asc())
        .all()
    )

    if not units:
        raise HTTPException(
            status_code=404,
            detail="No polling units found",
        )

    data = []

    for unit in units:

        target = unit.registration_target or 30
        registered = unit.registered_count or 0
        remaining = max(target - registered, 0)

        # Keep status synchronized
        current_status = (
            "FULL"
            if registered >= target
            else "OPEN"
        )

        data.append({
            "id": unit.id,
            "state_code": unit.state_code,
            "state_name": unit.state_name,

            "lga_code": unit.lga_code,
            "lga_name": unit.lga_name,

            "ward_code": unit.ward_code,
            "ward_name": unit.ward_name,

            "pu_code": unit.pu_code,
            "pu_name": unit.pu_name,
            "pu_location": unit.pu_location,

            "full_code": unit.full_code,
            "portal_id": unit.portal_id,

            "registration_target": target,
            "registered_count": registered,
            "remaining": remaining,
            "status": current_status,
        })

    return {
        "lga_code": lga_code,
        "ward_code": ward_code,
        "count": len(data),
        "data": data,
    }


# ============================================================
# SINGLE POLLING UNIT
# ============================================================

@router.get("/polling-units/{polling_unit_id}")
def polling_unit_details(
    polling_unit_id: int,
    db: Session = Depends(get_db),
):
    unit = (
        db.query(PollingUnit)
        .filter(PollingUnit.id == polling_unit_id)
        .first()
    )

    if not unit:
        raise HTTPException(
            status_code=404,
            detail="Polling unit not found",
        )

    target = unit.registration_target or 30
    registered = unit.registered_count or 0
    remaining = max(target - registered, 0)

    status = (
        "FULL"
        if registered >= target
        else "OPEN"
    )

    # Volunteers assigned to this exact PU
    volunteers = (
        db.query(Volunteer)
        .filter(
            Volunteer.polling_unit_id == unit.id
        )
        .order_by(Volunteer.id.desc())
        .all()
    )

    return {
        "polling_unit": {
            "id": unit.id,
            "state_code": unit.state_code,
            "state_name": unit.state_name,
            "lga_code": unit.lga_code,
            "lga_name": unit.lga_name,
            "ward_code": unit.ward_code,
            "ward_name": unit.ward_name,
            "pu_code": unit.pu_code,
            "pu_name": unit.pu_name,
            "pu_location": unit.pu_location,
            "full_code": unit.full_code,
            "portal_id": unit.portal_id,
            "registration_target": target,
            "registered_count": registered,
            "remaining": remaining,
            "status": status,
        },

        "volunteers": {
            "count": len(volunteers),
            "data": volunteers,
        },
    }


# ============================================================
# ALL POLLING UNITS
# ============================================================

@router.get("/polling-units")
def all_polling_units(
    db: Session = Depends(get_db),
    lga_code: Optional[str] = None,
    ward_code: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
):
    query = db.query(PollingUnit)

    if lga_code:
        query = query.filter(
            PollingUnit.lga_code == lga_code
        )

    if ward_code:
        query = query.filter(
            PollingUnit.ward_code == ward_code
        )

    if status:
        status = status.upper()

        if status not in ["OPEN", "FULL"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be OPEN or FULL",
            )

        query = query.filter(
            PollingUnit.status == status
        )

    query = query.order_by(
        PollingUnit.lga_code.asc(),
        PollingUnit.ward_code.asc(),
        PollingUnit.pu_code.asc(),
    )

    if limit:
        query = query.limit(limit)

    units = query.all()

    data = []

    for unit in units:
        target = unit.registration_target or 30
        registered = unit.registered_count or 0

        data.append({
            "id": unit.id,
            "lga_code": unit.lga_code,
            "lga_name": unit.lga_name,
            "ward_code": unit.ward_code,
            "ward_name": unit.ward_name,
            "pu_code": unit.pu_code,
            "pu_name": unit.pu_name,
            "pu_location": unit.pu_location,
            "full_code": unit.full_code,
            "registration_target": target,
            "registered_count": registered,
            "remaining": max(
                target - registered,
                0,
            ),
            "status": (
                "FULL"
                if registered >= target
                else "OPEN"
            ),
        })

    return {
        "count": len(data),
        "data": data,
    }


# ============================================================
# POLLING UNIT ANALYTICS
# ============================================================

@router.get("/analytics/polling-units")
def polling_unit_analytics(
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            PollingUnit.lga_code,
            PollingUnit.lga_name,
            func.count(PollingUnit.id).label(
                "polling_units"
            ),
            func.coalesce(
                func.sum(
                    PollingUnit.registration_target
                ),
                0,
            ).label("target"),
            func.coalesce(
                func.sum(
                    PollingUnit.registered_count
                ),
                0,
            ).label("registered"),
        )
        .group_by(
            PollingUnit.lga_code,
            PollingUnit.lga_name,
        )
        .order_by(PollingUnit.lga_code.asc())
        .all()
    )

    result = []

    for row in rows:

        target = int(row.target or 0)
        registered = int(row.registered or 0)

        result.append({
            "lga_code": row.lga_code,
            "lga": row.lga_name,
            "polling_units": row.polling_units,
            "target": target,
            "registered": registered,
            "remaining": max(
                target - registered,
                0,
            ),
        })

    return result


# ============================================================
# ALL VOLUNTEERS
# ============================================================

@router.get("/volunteers")
def all_volunteers(
    db: Session = Depends(get_db),
    limit: Optional[int] = None,
    sort: Optional[str] = None,
    polling_unit_id: Optional[int] = None,
    lga_code: Optional[str] = None,
    ward_code: Optional[str] = None,
):
    query = db.query(Volunteer)

    # Exact polling unit filter
    if polling_unit_id:
        query = query.filter(
            Volunteer.polling_unit_id == polling_unit_id
        )

    # Geographic filters through PollingUnit
    if lga_code or ward_code:

        query = query.join(
            PollingUnit,
            Volunteer.polling_unit_id == PollingUnit.id,
        )

        if lga_code:
            query = query.filter(
                PollingUnit.lga_code == lga_code
            )

        if ward_code:
            query = query.filter(
                PollingUnit.ward_code == ward_code
            )

    if sort:
        try:
            field, order = sort.split(":", 1)

            if hasattr(Volunteer, field):
                column = getattr(
                    Volunteer,
                    field,
                )

                if order.lower() == "desc":
                    query = query.order_by(
                        column.desc()
                    )
                else:
                    query = query.order_by(
                        column.asc()
                    )
            else:
                query = query.order_by(
                    Volunteer.id.desc()
                )

        except Exception:
            query = query.order_by(
                Volunteer.id.desc()
            )

    else:
        query = query.order_by(
            Volunteer.id.desc()
        )

    if limit:
        query = query.limit(limit)

    volunteers = query.all()

    return {
        "count": len(volunteers),
        "data": volunteers,
    }


# ============================================================
# RECENT VOLUNTEERS
# ============================================================

@router.get("/volunteers/recent")
def recent_volunteers(
    db: Session = Depends(get_db),
):
    volunteers = (
        db.query(Volunteer)
        .order_by(Volunteer.id.desc())
        .limit(5)
        .all()
    )

    return volunteers


# ============================================================
# SINGLE VOLUNTEER
# ============================================================

@router.get("/volunteer/{volunteer_id}")
def volunteer_details(
    volunteer_id: int,
    db: Session = Depends(get_db),
):
    volunteer = (
        db.query(Volunteer)
        .filter(Volunteer.id == volunteer_id)
        .first()
    )

    if not volunteer:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found",
        )

    polling_unit = None

    if volunteer.polling_unit_id:
        polling_unit = (
            db.query(PollingUnit)
            .filter(
                PollingUnit.id
                == volunteer.polling_unit_id
            )
            .first()
        )

    return {
        "volunteer": volunteer,

        "polling_unit": (
            {
                "id": polling_unit.id,
                "lga_code": polling_unit.lga_code,
                "lga_name": polling_unit.lga_name,
                "ward_code": polling_unit.ward_code,
                "ward_name": polling_unit.ward_name,
                "pu_code": polling_unit.pu_code,
                "pu_name": polling_unit.pu_name,
                "pu_location": polling_unit.pu_location,
                "full_code": polling_unit.full_code,
                "target": (
                    polling_unit.registration_target
                    or 30
                ),
                "registered": (
                    polling_unit.registered_count
                    or 0
                ),
                "remaining": max(
                    (
                        polling_unit.registration_target
                        or 30
                    )
                    - (
                        polling_unit.registered_count
                        or 0
                    ),
                    0,
                ),
                "status": (
                    "FULL"
                    if (
                        polling_unit.registered_count
                        or 0
                    )
                    >= (
                        polling_unit.registration_target
                        or 30
                    )
                    else "OPEN"
                ),
            }
            if polling_unit
            else None
        ),
    }


# ============================================================
# DELETE VOLUNTEER
# ============================================================

@router.delete("/volunteer/{volunteer_id}")
def delete_volunteer(
    volunteer_id: int,
    db: Session = Depends(get_db),
):
    volunteer = (
        db.query(Volunteer)
        .filter(Volunteer.id == volunteer_id)
        .first()
    )

    if not volunteer:
        raise HTTPException(
            status_code=404,
            detail="Volunteer not found",
        )

    # Remember the assigned polling unit
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

    # Remove uploaded files
    for file_path in [
        volunteer.passport,
        volunteer.qr_code,
        volunteer.id_card,
    ]:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    db.delete(volunteer)

    # Update polling unit registration count
    if polling_unit:

        current_count = (
            polling_unit.registered_count
            or 0
        )

        polling_unit.registered_count = max(
            current_count - 1,
            0,
        )

        target = (
            polling_unit.registration_target
            or 30
        )

        polling_unit.status = (
            "FULL"
            if polling_unit.registered_count >= target
            else "OPEN"
        )

    db.commit()

    return {
        "success": True,
        "message": "Volunteer deleted",

        "polling_unit": (
            {
                "id": polling_unit.id,
                "registered_count": (
                    polling_unit.registered_count
                ),
                "registration_target": (
                    polling_unit.registration_target
                    or 30
                ),
                "remaining": max(
                    (
                        polling_unit.registration_target
                        or 30
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
# SEARCH VOLUNTEERS
# ============================================================

@router.get("/search")
def search_volunteers(
    keyword: str,
    db: Session = Depends(get_db),
):
    keyword = keyword.strip()

    if not keyword:
        return []

    volunteers = (
        db.query(Volunteer)
        .filter(
            or_(
                Volunteer.name.ilike(
                    f"%{keyword}%"
                ),
                Volunteer.phone.ilike(
                    f"%{keyword}%"
                ),
                Volunteer.registration_no.ilike(
                    f"%{keyword}%"
                ),
            )
        )
        .order_by(Volunteer.id.desc())
        .all()
    )

    return volunteers


# ============================================================
# MEMBERSHIP CARD DOWNLOAD
# ============================================================

@router.get("/membership-card/{registration_no}")
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

    if not volunteer.id_card:
        raise HTTPException(
            status_code=404,
            detail="Membership card not found",
        )

    if not os.path.exists(volunteer.id_card):
        raise HTTPException(
            status_code=404,
            detail="Membership card file not found",
        )

    return FileResponse(
        volunteer.id_card,
        media_type="application/pdf",
        filename=(
            f"{registration_no}-membership-card.pdf"
        ),
    )


# ============================================================
# CURRENT ADMIN
# ============================================================

@router.get("/me")
def current_admin(
    current_user: dict = Depends(
        get_current_admin
    ),
):
    return {
        "username": current_user.get("sub"),
        "role": current_user.get("role"),
    }


# ============================================================
# EXPORT EXCEL
# ============================================================

@router.get("/export/excel")
def export_excel(
    db: Session = Depends(get_db),
):
    volunteers = (
        db.query(Volunteer)
        .order_by(Volunteer.id.desc())
        .all()
    )

    file_path = generate_volunteers_excel(
        volunteers
    )

    return FileResponse(
        file_path,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        filename=os.path.basename(file_path),
    )


# ============================================================
# LGA ANALYTICS
# ============================================================

@router.get("/analytics/lga")
def lga_analytics(
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            Volunteer.lga,
            func.count(Volunteer.id),
        )
        .group_by(Volunteer.lga)
        .order_by(
            func.count(Volunteer.id).desc()
        )
        .all()
    )

    return [
        {
            "lga": lga,
            "count": count,
        }
        for lga, count in results
    ]


# ============================================================
# GENDER ANALYTICS
# ============================================================

@router.get("/analytics/gender")
def gender_analytics(
    db: Session = Depends(get_db),
):
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
        "female": female,
    }


# ============================================================
# WARD ANALYTICS
# ============================================================

@router.get("/analytics/ward")
def ward_analytics(
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            Volunteer.lga,
            Volunteer.ward,
            func.count(Volunteer.id),
        )
        .group_by(
            Volunteer.lga,
            Volunteer.ward,
        )
        .order_by(
            func.count(Volunteer.id).desc()
        )
        .all()
    )

    return [
        {
            "lga": lga,
            "ward": ward,
            "count": count,
        }
        for lga, ward, count in results
    ]


# ============================================================
# POLLING UNIT VOLUNTEER ANALYTICS
# ============================================================

@router.get(
    "/analytics/polling-unit-volunteers"
)
def polling_unit_volunteer_analytics(
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            PollingUnit.id,
            PollingUnit.lga_name,
            PollingUnit.ward_name,
            PollingUnit.pu_code,
            PollingUnit.pu_name,
            PollingUnit.registration_target,
            PollingUnit.registered_count,
        )
        .order_by(
            PollingUnit.lga_code.asc(),
            PollingUnit.ward_code.asc(),
            PollingUnit.pu_code.asc(),
        )
        .all()
    )

    data = []

    for row in results:

        target = (
            row.registration_target
            or 30
        )

        registered = (
            row.registered_count
            or 0
        )

        data.append({
            "polling_unit_id": row.id,
            "lga": row.lga_name,
            "ward": row.ward_name,
            "pu_code": row.pu_code,
            "polling_unit": row.pu_name,
            "target": target,
            "registered": registered,
            "remaining": max(
                target - registered,
                0,
            ),
            "status": (
                "FULL"
                if registered >= target
                else "OPEN"
            ),
        })

    return {
        "count": len(data),
        "data": data,
    }


# ============================================================
# NOTIFICATIONS
# ============================================================

@router.get("/notifications")
def notifications():
    return []