"""Require a final session-history snapshot before analysis or export."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("calls") as batch:
        batch.add_column(sa.Column("evidence_complete", sa.Boolean(), nullable=False,
                                   server_default=sa.false()))
    with op.batch_alter_table("calls") as batch:
        batch.alter_column("evidence_complete", server_default=None)


def downgrade():
    with op.batch_alter_table("calls") as batch:
        batch.drop_column("evidence_complete")
