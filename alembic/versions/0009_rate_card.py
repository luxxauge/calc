"""Add rate card tables and optional item mapping for extras

Revision ID: 0009ratecard
Revises: 0008param
Create Date: 2026-01-30T08:19:39.925876Z
"""

from alembic import op
import sqlalchemy as sa

revision = "0009ratecard"
down_revision = "0008param"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "rate_card",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="EUR"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("uq_rate_card_name", "rate_card", ["name"], unique=True)
    op.create_index("ix_rate_card_name", "rate_card", ["name"])

    op.create_table(
        "rate_card_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rate_card_id", sa.Integer(), sa.ForeignKey("rate_card.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="pcs"),
        sa.Column("material_unit_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("labor_task_code", sa.String(length=64), nullable=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rate_card_line_rate_card_id", "rate_card_line", ["rate_card_id"])
    op.create_index("ix_rate_card_line_key", "rate_card_line", ["key"])

    op.add_column("calc_extra_line", sa.Column("item_id", sa.Integer(), nullable=True))

def downgrade():
    op.drop_column("calc_extra_line", "item_id")
    op.drop_index("ix_rate_card_line_key", table_name="rate_card_line")
    op.drop_index("ix_rate_card_line_rate_card_id", table_name="rate_card_line")
    op.drop_table("rate_card_line")
    op.drop_index("ix_rate_card_name", table_name="rate_card")
    op.drop_index("uq_rate_card_name", table_name="rate_card")
    op.drop_table("rate_card")
