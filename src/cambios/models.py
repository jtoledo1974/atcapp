"""Database models for the application."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import db


class User(db.Model):
    """User model."""

    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(80), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    license_number = Column(String(50), nullable=False)


class Shift(db.Model):
    """Shift model."""

    __tablename__ = "shifts"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    shift_type = Column(
        String(10),
        ForeignKey("shift_types.code"),
        nullable=False,
    )  # This now references the primary key of ShiftTypes
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", backref="shifts")
    shift_type_details = relationship(
        "ShiftTypes",
        back_populates="shifts",
    )  # Optionally, to access ShiftTypes from Shift


class ShiftTypes(db.Model):
    """Shift types model."""

    __tablename__ = "shift_types"
    code = Column(String(10), primary_key=True, nullable=False)
    description = Column(String(50), nullable=False)
    shifts = relationship(
        "Shift",
        back_populates="shift_type_details",
    )  # This tells SQLAlchemy how to navigate back from ShiftTypes to Shift
