"""Database models for the application."""

from .database import db


class User(db.Model):
    """User model."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)


class Shift(db.Model):
    """Shift model."""

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    shift_type = db.Column(db.String(1), nullable=False)  # 'M', 'T', or 'N'
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("shifts", lazy=True))
