"""inspection order distribution link

Revision ID: 0013inspectionorderdist
Revises: 0012inspectionmvp
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0013inspectionorderdist"
down_revision = "0012inspectionmvp"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "insp_inspection_order_distribution",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_order_id", sa.Integer(), sa.ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False),
        sa.Column("distribution_id", sa.Integer(), sa.ForeignKey("insp_distribution.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("inspection_order_id", "distribution_id", name="uq_insp_order_distribution"),
    )
    op.create_index("ix_insp_order_dist_tenant_id", "insp_inspection_order_distribution", ["tenant_id"])
    op.create_index("ix_insp_order_dist_order_id", "insp_inspection_order_distribution", ["inspection_order_id"])
    op.create_index("ix_insp_order_dist_distribution_id", "insp_inspection_order_distribution", ["distribution_id"])


def downgrade():
    op.drop_index("ix_insp_order_dist_distribution_id", table_name="insp_inspection_order_distribution")
    op.drop_index("ix_insp_order_dist_order_id", table_name="insp_inspection_order_distribution")
    op.drop_index("ix_insp_order_dist_tenant_id", table_name="insp_inspection_order_distribution")
    op.drop_table("insp_inspection_order_distribution")
