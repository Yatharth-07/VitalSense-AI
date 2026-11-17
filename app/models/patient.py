from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime
from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    # Email must NOT have unique=True because the assignment includes repeated/duplicate records
    email = Column(String(255), nullable=False, index=True)
    glucose = Column(Float, nullable=False)
    haemoglobin = Column(Float, nullable=False)
    cholesterol = Column(Float, nullable=False)
    remarks = Column(Text, nullable=True)
    ai_insights_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Patient(id={self.id}, full_name='{self.full_name}', email='{self.email}')>"
