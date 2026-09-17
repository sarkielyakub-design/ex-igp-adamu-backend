from sqlalchemy.orm import Session

from app.models.volunteer import Volunteer


def generate_registration_no(db: Session) -> str:
    """Generate the next EIAYV Nasarawa registration number."""

    last_id = (
        db.query(Volunteer.id)
        .order_by(Volunteer.id.desc())
        .scalar()
    )

    next_id = (last_id or 0) + 1

    return f"EIAYV-NS-{next_id:06d}"