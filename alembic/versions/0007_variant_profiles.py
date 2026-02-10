"""Add variant profiles and rules

Revision ID: 0007variant
Revises: 0006calctrace
Create Date: 2026-01-30T08:12:14.469350Z
"""

from alembic import op
import sqlalchemy as sa

revision = "0007variant"
down_revision = "0006calctrace"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "variant_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("default_overhead_pct", sa.String(length=16), nullable=False, server_default="0.15"),
        sa.Column("default_profit_pct", sa.String(length=16), nullable=False, server_default="0.10"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("uq_variant_profile_key", "variant_profile", ["key"], unique=True)
    op.create_index("ix_variant_profile_key", "variant_profile", ["key"])

    op.create_table(
        "variant_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_profile_id", sa.Integer(), sa.ForeignKey("variant_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_task_code", sa.String(length=64), nullable=True),
        sa.Column("match_pattern", sa.String(length=255), nullable=True),
        sa.Column("is_regex", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("labor_multiplier", sa.String(length=16), nullable=False, server_default="1.00"),
        sa.Column("material_multiplier", sa.String(length=16), nullable=False, server_default="1.00"),
        sa.Column("add_labor_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_variant_rule_variant_profile_id", "variant_rule", ["variant_profile_id"])

def downgrade():
    op.drop_index("ix_variant_rule_variant_profile_id", table_name="variant_rule")
    op.drop_table("variant_rule")
    op.drop_index("ix_variant_profile_key", table_name="variant_profile")
    op.drop_index("uq_variant_profile_key", table_name="variant_profile")
    op.drop_table("variant_profile")
