"""Add calc estimate tables

Revision ID: 0004calc
Revises: 0003lv
Create Date: 2026-01-30T08:03:13.169759Z
"""

from alembic import op
import sqlalchemy as sa

revision = "0004calc"
down_revision = "0003lv"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "calc_estimate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lv_document_id", sa.Integer(), sa.ForeignKey("lv_document.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant", sa.String(length=16), nullable=False),
        sa.Column("labor_rate_cent", sa.Integer(), nullable=False, server_default="6500"),
        sa.Column("overhead_pct", sa.String(length=16), nullable=False, server_default="0.15"),
        sa.Column("profit_pct", sa.String(length=16), nullable=False, server_default="0.10"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_calc_estimate_lv_document_id", "calc_estimate", ["lv_document_id"])

    op.create_table(
        "calc_estimate_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estimate_id", sa.Integer(), sa.ForeignKey("calc_estimate.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lv_position_id", sa.Integer(), sa.ForeignKey("lv_position.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qty", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="pcs"),
        sa.Column("material_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("labor_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("labor_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cent", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_calc_estimate_line_estimate_id", "calc_estimate_line", ["estimate_id"])
    op.create_index("ix_calc_estimate_line_lv_position_id", "calc_estimate_line", ["lv_position_id"])

def downgrade():
    op.drop_index("ix_calc_estimate_line_lv_position_id", table_name="calc_estimate_line")
    op.drop_index("ix_calc_estimate_line_estimate_id", table_name="calc_estimate_line")
    op.drop_table("calc_estimate_line")
    op.drop_index("ix_calc_estimate_lv_document_id", table_name="calc_estimate")
    op.drop_table("calc_estimate")
