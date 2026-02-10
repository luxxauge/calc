"""Add LV (Bill of Quantities) tables

Revision ID: 0003lv
Revises: 0002catalogitems
Create Date: 2026-01-30T08:00:05.550816Z
"""

from alembic import op
import sqlalchemy as sa

revision = "0003lv"
down_revision = "0002catalogitems"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "lv_document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False, server_default="xlsx"),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_lv_document_project_id", "lv_document", ["project_id"])

    op.create_table(
        "lv_position",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lv_document_id", sa.Integer(), sa.ForeignKey("lv_document.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pos_no", sa.String(length=64), nullable=True),
        sa.Column("short_text", sa.String(length=255), nullable=False),
        sa.Column("long_text", sa.Text(), nullable=True),
        sa.Column("qty", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="pcs"),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_lv_position_lv_document_id", "lv_position", ["lv_document_id"])

    op.create_table(
        "lv_position_match",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lv_position_id", sa.Integer(), sa.ForeignKey("lv_position.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id", ondelete="SET NULL"), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("lv_position_id", name="uq_lv_position_match_position"),
    )
    op.create_index("ix_lv_position_match_item_id", "lv_position_match", ["item_id"])

def downgrade():
    op.drop_index("ix_lv_position_match_item_id", table_name="lv_position_match")
    op.drop_table("lv_position_match")
    op.drop_index("ix_lv_position_lv_document_id", table_name="lv_position")
    op.drop_table("lv_position")
    op.drop_index("ix_lv_document_project_id", table_name="lv_document")
    op.drop_table("lv_document")
