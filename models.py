"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True)
    status = Column(String(20), nullable=False, default="queued")
    url = Column(Text, nullable=False)
    method = Column(String(20))
    length = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    statistics = Column(JSON, nullable=True)
    files_created = Column(JSON, nullable=True)
    method_used = Column(String(30), nullable=True)
    execution_time = Column(Float, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "url": self.url,
            "method": self.method,
            "length": self.length,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "summary": self.summary,
            "error": self.error,
            "statistics": self.statistics,
            "files_created": self.files_created,
            "method_used": self.method_used,
            "execution_time": self.execution_time,
        }
