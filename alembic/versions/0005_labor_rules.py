"""Add labor tasks and rules

Revision ID: 0005labor
Revises: 0004calc
Create Date: 2026-01-30T08:05:47.149730Z
"""

from alembic import op
import sqlalchemy as sa

revision = "0005labor"
down_revision = "0004calc"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "labor_task",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="pcs"),
        sa.Column("minutes_per_unit", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("uq_labor_task_code", "labor_task", ["code"], unique=True)
    op.create_index("ix_labor_task_code", "labor_task", ["code"])

    op.create_table(
        "labor_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pattern", sa.String(length=255), nullable=False),
        sa.Column("is_regex", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("labor_task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_labor_rule_task_id", "labor_rule", ["task_id"])

def downgrade():
    op.drop_index("ix_labor_rule_task_id", table_name="labor_rule")
    op.drop_table("labor_rule")
    op.drop_index("ix_labor_task_code", table_name="labor_task")
    op.drop_index("uq_labor_task_code", table_name="labor_task")
    op.drop_table("labor_task")
