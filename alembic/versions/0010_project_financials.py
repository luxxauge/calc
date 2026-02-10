"""project financial inputs

Revision ID: 0010_project_financials
Revises: 0010paramrules
Create Date: 2026-01-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_project_financials"
down_revision = "0010paramrules"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("prj_project_inputs", sa.Column("labor_rate_eur_h", sa.String(length=16), nullable=False, server_default="72"))
    op.add_column("prj_project_inputs", sa.Column("overhead_pct", sa.String(length=16), nullable=False, server_default="0"))
    op.add_column("prj_project_inputs", sa.Column("profit_pct", sa.String(length=16), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("prj_project_inputs", "profit_pct")
    op.drop_column("prj_project_inputs", "overhead_pct")
    op.drop_column("prj_project_inputs", "labor_rate_eur_h")
