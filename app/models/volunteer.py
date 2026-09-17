from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func

from app.db.session import Base
from sqlalchemy import ForeignKey


class Volunteer(Base):
    __tablename__ = "volunteers"

    # ============================================================
    # PRIMARY KEY
    # ============================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ============================================================
    # REGISTRATION
    # ============================================================

    registration_no = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # ============================================================
    # FILES
    # ============================================================

    passport = Column(String(500))

    qr_code = Column(String(500))

    id_card = Column(String(500))

    # ============================================================
    # PERSONAL INFORMATION
    # ============================================================

    name = Column(
        String(255),
        nullable=False,
    )

    phone = Column(
        String(20),
        nullable=False,
    )

    gender = Column(
        String(20),
    )

    age = Column(
        Integer,
    )

    # ============================================================
    # LOCATION
    # ============================================================
    # Keep these fields because they already exist in your system.
    # polling_unit_id connects the volunteer to the real
    # INEC Polling Unit record.

    lga = Column(
        String(100),
        index=True,
    )

    ward = Column(
        String(100),
        index=True,
    )

    unit = Column(
        String(100),
        index=True,
    )

    polling_unit_id = Column(
        Integer,
        ForeignKey("polling_units.id"),
        nullable=True,
        index=True,
    )

    # ============================================================
    # EDUCATION
    # ============================================================

    highest_qualification = Column(
        String(255),
    )

    additional_qualification = Column(
        String(255),
    )

    specialization = Column(
        String(255),
    )

    # ============================================================
    # EMPLOYMENT
    # ============================================================

    employment_status = Column(
        String(100),
    )

    # ============================================================
    # PHYSICAL STATUS
    # ============================================================

    physically_challenged = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ============================================================
    # ORGANIZATION
    # ============================================================

    youth_org_member = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    organization_name = Column(
        String(255),
    )

    position = Column(
        String(255),
    )

    # ============================================================
    # EXPECTATION
    # ============================================================

    expectation = Column(
        Text,
    )

    # ============================================================
    # TIMESTAMP
    # ============================================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    polling_unit_id = Column(
    Integer,
    ForeignKey("polling_units.id"),
    nullable=True,
    index=True,
)