"""Create assessment tables and a single persistent call-admission counter."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "control",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("active_call_id", sa.String(36)),
    )
    op.bulk_insert(sa.table("control", sa.column("id"), sa.column("attempts")), [{"id": 1, "attempts": 0}])
    op.create_table(
        "calls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_key", sa.String(100), unique=True, nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("room_name", sa.String(80), unique=True, nullable=False),
        sa.Column("dispatch_id", sa.String(100)),
        sa.Column("worker_claimed", sa.Boolean(), nullable=False),
        sa.Column("dial_started", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("transcript", sa.JSON(), nullable=False),
        sa.Column("tool_events", sa.JSON(), nullable=False),
        sa.Column("recording", sa.JSON(), nullable=False),
        sa.Column("analysis", sa.JSON()),
        sa.Column("analysis_status", sa.String(30), nullable=False),
        sa.Column("export_status", sa.String(30), nullable=False),
        sa.Column("finalization_status", sa.String(30), nullable=False),
        sa.Column("finalization_until", sa.DateTime(timezone=True)),
        sa.Column("report", sa.JSON()),
        sa.Column("trace_id", sa.String(36)),
        sa.Column("trace_url", sa.Text()),
        sa.Column("evaluation", sa.JSON(), nullable=False),
        sa.Column("evaluation_checked_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
    )
    op.create_table(
        "appointment_slots",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("doctor", sa.String(100), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("call_id", sa.String(36), sa.ForeignKey("calls.id"), unique=True, nullable=False),
        sa.Column("slot_id", sa.String(50), sa.ForeignKey("appointment_slots.id"), unique=True, nullable=False),
        sa.Column("confirmation_evidence", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("bookings")
    op.drop_table("appointment_slots")
    op.drop_table("calls")
    op.drop_table("control")
