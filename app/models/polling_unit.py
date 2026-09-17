from sqlalchemy import Column, Integer, String

from app.db.session import Base


class PollingUnit(Base):
    __tablename__ = "polling_units"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ========================================================
    # STATE
    # ========================================================

    state_code = Column(
        String(10),
        nullable=False,
        index=True,
    )

    state_name = Column(
        String(100),
        nullable=False,
    )

    # ========================================================
    # LGA
    # ========================================================

    lga_code = Column(
        String(10),
        nullable=False,
        index=True,
    )

    lga_name = Column(
        String(100),
        nullable=False,
        index=True,
    )

    # ========================================================
    # REGISTRATION AREA / WARD
    # ========================================================

    ward_code = Column(
        String(10),
        nullable=False,
        index=True,
    )

    ward_name = Column(
        String(150),
        nullable=False,
        index=True,
    )

    # ========================================================
    # POLLING UNIT
    # ========================================================

    pu_code = Column(
        String(20),
        nullable=False,
    )

    pu_name = Column(
        String(255),
        nullable=False,
        index=True,
    )

    pu_location = Column(
        String(500),
        nullable=True,
    )

    # ========================================================
    # OFFICIAL FULL CODE
    # Example:
    # 26/01/01/001
    # ========================================================

    full_code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # INEC portal ID where available
    portal_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    # ========================================================
    # REGISTRATION CAPACITY
    # ========================================================

    registration_target = Column(
        Integer,
        nullable=False,
        default=30,
    )

    registered_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    status = Column(
        String(20),
        nullable=False,
        default="OPEN",
        index=True,
    )