"""Add item catalog tables

Revision ID: 0002catalogitems
Revises: 0001
Create Date: 2026-01-30T07:24:53.589247Z
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002catalogitems"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_no", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manufacturer", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="pcs"),
        sa.Column("vat_rate", sa.String(length=16), nullable=False, server_default="0.19"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("article_no","manufacturer", name="uq_item_article_manufacturer"),
    )
    op.create_index("ix_item_article_no", "item", ["article_no"])

    op.create_table(
        "item_price",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_ek_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_vk_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="EUR"),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_item_price_item_id", "item_price", ["item_id"])

    op.create_table(
        "import_batch",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )

def downgrade():
    op.drop_table("import_batch")
    op.drop_index("ix_item_price_item_id", table_name="item_price")
    op.drop_table("item_price")
    op.drop_index("ix_item_article_no", table_name="item")
    op.drop_table("item")
