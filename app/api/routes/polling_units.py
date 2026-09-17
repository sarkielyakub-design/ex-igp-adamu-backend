from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.db.session import get_db
from app.models.polling_unit import PollingUnit


router = APIRouter(
    prefix="/api/polling-units",
    tags=["Polling Units"],
)


# ============================================================
# LIST NASARAWA LGAs
# ============================================================

@router.get("/lgas")
def list_lgas(
    db: Session = Depends(get_db),
):
    """
    Public list of Nasarawa State LGAs represented
    in the polling-unit dataset.
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
        .filter(PollingUnit.state_code == "25")
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
            "polling_units": int(row.polling_units or 0),
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

@router.get("/wards")
def list_wards(
    lga_code: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Return wards/registration areas for a selected LGA.
    """

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
        .filter(
            PollingUnit.state_code == "25",
            PollingUnit.lga_code == lga_code,
        )
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
            detail="LGA not found or has no wards",
        )

    data = []

    for row in rows:
        target = int(row.target or 0)
        registered = int(row.registered or 0)

        data.append({
            "ward_code": row.ward_code,
            "ward_name": row.ward_name,
            "polling_units": int(row.polling_units or 0),
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
# LIST POLLING UNITS
# ============================================================

@router.get("")
def list_polling_units(
    lga_code: Optional[str] = None,
    ward_code: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Public polling-unit list.

    Can be filtered by:
        lga_code
        ward_code
        status
    """

    query = (
        db.query(PollingUnit)
        .filter(PollingUnit.state_code == "25")
    )

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

    units = (
        query
        .order_by(
            PollingUnit.lga_code.asc(),
            PollingUnit.ward_code.asc(),
            PollingUnit.pu_code.asc(),
        )
        .all()
    )

    data = []

    for unit in units:
        target = unit.registration_target or 30
        registered = unit.registered_count or 0
        remaining = max(target - registered, 0)

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
        "count": len(data),
        "data": data,
    }


# ============================================================
# SINGLE POLLING UNIT
# ============================================================

@router.get("/{polling_unit_id}")
def get_polling_unit(
    polling_unit_id: int,
    db: Session = Depends(get_db),
):
    """
    Return one public polling unit and its current capacity.
    """

    unit = (
        db.query(PollingUnit)
        .filter(
            PollingUnit.id == polling_unit_id,
            PollingUnit.state_code == "25",
        )
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

    return {
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
    }