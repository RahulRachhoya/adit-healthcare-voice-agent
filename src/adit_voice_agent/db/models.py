"""Database tables. JSON values are replaced on update, never mutated in place."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Control(Base):
    __tablename__ = "control"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    attempts: Mapped[int] = mapped_column(default=0)
    active_call_id: Mapped[str | None] = mapped_column(String(36))


class Call(Base):
    __tablename__ = "calls"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_key: Mapped[str] = mapped_column(String(100), unique=True)
    request_digest: Mapped[str] = mapped_column(String(64))
    room_name: Mapped[str] = mapped_column(String(80), unique=True)
    dispatch_id: Mapped[str | None] = mapped_column(String(100))
    worker_claimed: Mapped[bool] = mapped_column(default=False)
    dial_started: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    input_data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_complete: Mapped[bool] = mapped_column(default=False)
    transcript: Mapped[list] = mapped_column(JSON, default=list)
    tool_events: Mapped[list] = mapped_column(JSON, default=list)
    recording: Mapped[dict] = mapped_column(JSON, default=dict)
    analysis: Mapped[dict | None] = mapped_column(JSON)
    analysis_status: Mapped[str] = mapped_column(String(30), default="pending")
    export_status: Mapped[str] = mapped_column(String(30), default="pending")
    finalization_status: Mapped[str] = mapped_column(String(30), default="pending")
    finalization_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report: Mapped[dict | None] = mapped_column(JSON)
    trace_id: Mapped[str | None] = mapped_column(String(36))
    trace_url: Mapped[str | None] = mapped_column(Text)
    evaluation: Mapped[dict] = mapped_column(JSON, default=dict)
    evaluation_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class Slot(Base):
    __tablename__ = "appointment_slots"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    doctor: Mapped[str] = mapped_column(String(100))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(80))


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("calls.id"), unique=True)
    slot_id: Mapped[str] = mapped_column(ForeignKey("appointment_slots.id"), unique=True)
    confirmation_evidence: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
