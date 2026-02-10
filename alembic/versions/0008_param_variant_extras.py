"""Add parameter-based variant extras + building type inputs

Revision ID: 0008param
Revises: 0007variant
Create Date: 2026-01-30T08:16:43.458169Z
"""

from alembic import op
import sqlalchemy as sa

revision = "0008param"
down_revision = "0007variant"
branch_labels = None
depends_on = None

def upgrade():
    # project inputs
    op.add_column("prj_project_inputs", sa.Column("building_type", sa.String(length=16), nullable=False, server_default="efh"))
    op.add_column("prj_project_inputs", sa.Column("apartments", sa.Integer(), nullable=True))

    # calc extra lines (variant-generated)
    op.create_table(
        "calc_extra_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estimate_id", sa.Integer(), sa.ForeignKey("calc_estimate.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("qty", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="pcs"),
        sa.Column("material_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("labor_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("labor_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="variant_param"),
        sa.Column("note", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_calc_extra_line_estimate_id", "calc_extra_line", ["estimate_id"])

def downgrade():
    op.drop_index("ix_calc_extra_line_estimate_id", table_name="calc_extra_line")
    op.drop_table("calc_extra_line")
    op.drop_column("prj_project_inputs", "apartments")
    op.drop_column("prj_project_inputs", "building_type")
