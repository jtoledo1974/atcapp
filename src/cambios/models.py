"""Database models for the application."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import db

# This is a hack due to flask_sqlalchemy seeeming incompatible with mypy
# It is explained in https://github.com/pallets-eco/flask-sqlalchemy/issues/1327
# I've tried all approaches and this seems to me the simplest hack
# to get mypy happy.
# We don't get autocomplete for model methods like query, but at least
# we do get type checking of columns.


class User(db.Model):  # type: ignore[name-defined]
    """User model."""

    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    firebase_uid = Column(String, unique=True)
    email: str = Column(String(80), unique=True, nullable=False)  # type: ignore[assignment]
    first_name: str = Column(String(100), nullable=False)  # type: ignore[assignment]
    last_name: str = Column(String(100), nullable=False)  # type: ignore[assignment]
    category: str = Column(String(50), nullable=False)  # type: ignore[assignment]
    team: str = Column(String(1))  # type: ignore[assignment]
    license_number: str = Column(String(50), nullable=False)  # type: ignore[assignment]
    is_admin: bool = Column(Boolean, default=False)  # type: ignore[assignment]
    has_accepted_terms: bool = Column(Boolean, default=False)  # type: ignore[assignment]


class Shift(db.Model):  # type: ignore[name-defined]
    """Shift model."""

    __tablename__ = "shifts"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    shift_type: str = Column(
        String(10),
        nullable=False,
    )  # type: ignore[assignment]
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", backref="shifts")


class ShiftTypes(db.Model):  # type: ignore[name-defined]
    """Shift types model."""

    __tablename__ = "shift_types"
    code: str = Column(String(10), primary_key=True, nullable=False)  # type: ignore[assignment]
    description: str = Column(String(50), nullable=False)  # type: ignore[assignment]
