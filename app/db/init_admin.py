from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash


def create_default_admin():
    db: Session = SessionLocal()

    try:
        admin = db.query(User).filter(
            User.username == "exigpadamuyouthvolunteers@gmail.com"
        ).first()

        if not admin:
            admin = User(
                username="exigpadamuyouthvolunteers@gmail.com",
                hashed_password=get_password_hash("Volunteer@2343"),
                role="admin"
            )

            db.add(admin)
            db.commit()

            print("✅ Default admin created")

        else:
            print("✅ Default admin already exists")

    finally:
        db.close()