"""Add parametrische Regeln table

Revision ID: 0010paramrules
Revises: 0009ratecard
Create Date: 2026-01-30T08:23:22.457757Z
"""

from alembic import op
import sqlalchemy as sa

revision = "0010paramrules"
down_revision = "0009ratecard"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "param_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("variant_key", sa.String(length=32), nullable=False, server_default="komfort"),
        sa.Column("building_type", sa.String(length=16), nullable=False, server_default="any"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("rate_key", sa.String(length=64), nullable=False),
        sa.Column("description_tpl", sa.String(length=255), nullable=False, server_default="{{rate_key}} (param)"),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="pcs"),
        sa.Column("qty_expr", sa.String(length=255), nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_param_rule_priority", "param_rule", ["priority"])
    op.create_index("ix_param_rule_variant_key", "param_rule", ["variant_key"])
    op.create_index("ix_param_rule_building_type", "param_rule", ["building_type"])

def downgrade():
    op.drop_index("ix_param_rule_building_type", table_name="param_rule")
    op.drop_index("ix_param_rule_variant_key", table_name="param_rule")
    op.drop_index("ix_param_rule_priority", table_name="param_rule")
    op.drop_table("param_rule")
