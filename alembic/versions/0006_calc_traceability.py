"""Add calc traceability columns

Revision ID: 0006calctrace
Revises: 0005labor
Create Date: 2026-01-30T08:07:33.544751Z
"""

from alembic import op
import sqlalchemy as sa

revision = "0006calctrace"
down_revision = "0005labor"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("calc_estimate_line", sa.Column("labor_source", sa.String(length=16), nullable=False, server_default="heuristic"))
    op.add_column("calc_estimate_line", sa.Column("labor_task_code", sa.String(length=64), nullable=True))
    op.add_column("calc_estimate_line", sa.Column("labor_rule_info", sa.String(length=255), nullable=True))

def downgrade():
    op.drop_column("calc_estimate_line", "labor_rule_info")
    op.drop_column("calc_estimate_line", "labor_task_code")
    op.drop_column("calc_estimate_line", "labor_source")
