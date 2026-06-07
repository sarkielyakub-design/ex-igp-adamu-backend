from sqlalchemy.orm import Session
from app.models.volunteer import Volunteer


def generate_registration_no(db: Session):

    last = db.query(Volunteer)\
        .order_by(Volunteer.id.desc())\
        .first()

    if not last:
        return "EIAYV-NS-000001"

    next_id = last.id + 1

    return f"EIAYV-NS-{next_id:06d}"