"""inspection mvp foundation

Revision ID: 0012inspectionmvp
Revises: 0011planqtymap
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0012inspectionmvp"
down_revision = "0011planqtymap"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "insp_tenant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "insp_customer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_insp_customer_tenant_id", "insp_customer", ["tenant_id"])

    op.create_table(
        "insp_site",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("insp_customer.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
    )
    op.create_index("ix_insp_site_tenant_id", "insp_site", ["tenant_id"])
    op.create_index("ix_insp_site_customer_id", "insp_site", ["customer_id"])

    op.create_table(
        "insp_object",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("insp_customer.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("insp_site.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
    )
    op.create_index("ix_insp_object_tenant_id", "insp_object", ["tenant_id"])
    op.create_index("ix_insp_object_customer_id", "insp_object", ["customer_id"])
    op.create_index("ix_insp_object_site_id", "insp_object", ["site_id"])

    op.create_table(
        "insp_distribution",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_id", sa.Integer(), sa.ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
    )
    op.create_index("ix_insp_distribution_tenant_id", "insp_distribution", ["tenant_id"])
    op.create_index("ix_insp_distribution_object_id", "insp_distribution", ["object_id"])

    op.create_table(
        "insp_inspection_order",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_id", sa.Integer(), sa.ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status in ('draft','planned','in_progress','technical_done','finalized','archived')", name="ck_insp_order_status"),
    )
    op.create_index("ix_insp_inspection_order_tenant_id", "insp_inspection_order", ["tenant_id"])
    op.create_index("ix_insp_inspection_order_object_id", "insp_inspection_order", ["object_id"])

    op.create_table(
        "insp_measurement_set",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_order_id", sa.Integer(), sa.ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
    )
    op.create_index("ix_insp_measurement_set_tenant_id", "insp_measurement_set", ["tenant_id"])
    op.create_index("ix_insp_measurement_set_inspection_order_id", "insp_measurement_set", ["inspection_order_id"])

    op.create_table(
        "insp_measurement",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("measurement_set_id", sa.Integer(), sa.ForeignKey("insp_measurement_set.id", ondelete="CASCADE"), nullable=False),
        sa.Column("point_label", sa.String(length=120), nullable=False),
        sa.Column("measured_value", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_insp_measurement_tenant_id", "insp_measurement", ["tenant_id"])
    op.create_index("ix_insp_measurement_measurement_set_id", "insp_measurement", ["measurement_set_id"])

    op.create_table(
        "insp_defect",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_order_id", sa.Integer(), sa.ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_id", sa.Integer(), sa.ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.CheckConstraint("status in ('open','assessed','deadline_set','follow_up','rechecked','closed')", name="ck_insp_defect_status"),
    )
    op.create_index("ix_insp_defect_tenant_id", "insp_defect", ["tenant_id"])
    op.create_index("ix_insp_defect_inspection_order_id", "insp_defect", ["inspection_order_id"])
    op.create_index("ix_insp_defect_object_id", "insp_defect", ["object_id"])

    op.create_table(
        "insp_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_order_id", sa.Integer(), sa.ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.CheckConstraint("status in ('draft','for_approval','approved','finalized','published','archived')", name="ck_insp_report_status"),
    )
    op.create_index("ix_insp_report_tenant_id", "insp_report", ["tenant_id"])
    op.create_index("ix_insp_report_inspection_order_id", "insp_report", ["inspection_order_id"])


def downgrade():
    op.drop_index("ix_insp_report_inspection_order_id", table_name="insp_report")
    op.drop_index("ix_insp_report_tenant_id", table_name="insp_report")
    op.drop_table("insp_report")

    op.drop_index("ix_insp_defect_object_id", table_name="insp_defect")
    op.drop_index("ix_insp_defect_inspection_order_id", table_name="insp_defect")
    op.drop_index("ix_insp_defect_tenant_id", table_name="insp_defect")
    op.drop_table("insp_defect")

    op.drop_index("ix_insp_measurement_measurement_set_id", table_name="insp_measurement")
    op.drop_index("ix_insp_measurement_tenant_id", table_name="insp_measurement")
    op.drop_table("insp_measurement")

    op.drop_index("ix_insp_measurement_set_inspection_order_id", table_name="insp_measurement_set")
    op.drop_index("ix_insp_measurement_set_tenant_id", table_name="insp_measurement_set")
    op.drop_table("insp_measurement_set")

    op.drop_index("ix_insp_inspection_order_object_id", table_name="insp_inspection_order")
    op.drop_index("ix_insp_inspection_order_tenant_id", table_name="insp_inspection_order")
    op.drop_table("insp_inspection_order")

    op.drop_index("ix_insp_distribution_object_id", table_name="insp_distribution")
    op.drop_index("ix_insp_distribution_tenant_id", table_name="insp_distribution")
    op.drop_table("insp_distribution")

    op.drop_index("ix_insp_object_site_id", table_name="insp_object")
    op.drop_index("ix_insp_object_customer_id", table_name="insp_object")
    op.drop_index("ix_insp_object_tenant_id", table_name="insp_object")
    op.drop_table("insp_object")

    op.drop_index("ix_insp_site_customer_id", table_name="insp_site")
    op.drop_index("ix_insp_site_tenant_id", table_name="insp_site")
    op.drop_table("insp_site")

    op.drop_index("ix_insp_customer_tenant_id", table_name="insp_customer")
    op.drop_table("insp_customer")

    op.drop_table("insp_tenant")
