from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.volunteer import Volunteer


def generate_registration_no(db: Session) -> str:
    """
    Generate the next volunteer registration number.

    Format:
        EIAYV-NS-000001
        EIAYV-NS-000002
        EIAYV-NS-000003
        ...

    The Volunteer database ID is used as the sequence source.
    """

    last_id = (
        db.query(func.max(Volunteer.id))
        .scalar()
    )

    next_id = (last_id or 0) + 1

    return f"EIAYV-NS-{next_id:06d}"