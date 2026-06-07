from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime
)
from sqlalchemy.sql import func

from app.db.session import Base


class Volunteer(Base):
    __tablename__ = "volunteers"

    id = Column(Integer, primary_key=True, index=True)

    registration_no = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )

    # Files
    passport = Column(String(500))
    qr_code = Column(String(500))
    id_card = Column(String(500))

    # Personal Info
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)

    gender = Column(String(20))
    age = Column(Integer)

    lga = Column(String(100))
    ward = Column(String(100))
    unit = Column(String(100))

    # Education
    highest_qualification = Column(String(255))
    additional_qualification = Column(String(255))

    specialization = Column(String(255))

    # Employment
    employment_status = Column(String(100))

    physically_challenged = Column(
        Boolean,
        default=False
    )

    # Organization
    youth_org_member = Column(
        Boolean,
        default=False
    )

    organization_name = Column(String(255))
    position = Column(String(255))

    expectation = Column(Text)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )