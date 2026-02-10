"""plan quantities mapping

Revision ID: 0011planqtymap
Revises: 0010_project_financials
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0011planqtymap"
down_revision = "0010_project_financials"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "prj_plan_qty_mapping",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("prj_project.id"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("variant_key", sa.String(length=32), nullable=True),
        sa.Column("rate_key", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False, server_default="St"),
        sa.Column("qty_factor", sa.String(length=16), nullable=False, server_default="1"),
        sa.Column("description", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_prj_plan_qty_mapping_project_id", "prj_plan_qty_mapping", ["project_id"])
    op.create_index(
        "ix_prj_plan_qty_mapping_kind_key",
        "prj_plan_qty_mapping",
        ["project_id", "kind", "key", "variant_key"],
    )


def downgrade():
    op.drop_index("ix_prj_plan_qty_mapping_kind_key", table_name="prj_plan_qty_mapping")
    op.drop_index("ix_prj_plan_qty_mapping_project_id", table_name="prj_plan_qty_mapping")
    op.drop_table("prj_plan_qty_mapping")
