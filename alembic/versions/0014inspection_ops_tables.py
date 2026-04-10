"""inspection operational tables

Revision ID: 0014inspectionopstables
Revises: 0013inspectionorderdist
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0014inspectionopstables"
down_revision = "0013inspectionorderdist"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "insp_appointment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_order_id", sa.Integer(), sa.ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_insp_appointment_tenant_id", "insp_appointment", ["tenant_id"])
    op.create_index("ix_insp_appointment_inspection_order_id", "insp_appointment", ["inspection_order_id"])

    op.create_table(
        "insp_distribution_report",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("insp_report.id", ondelete="CASCADE"), nullable=False),
        sa.Column("distribution_id", sa.Integer(), sa.ForeignKey("insp_distribution.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.UniqueConstraint("report_id", "distribution_id", name="uq_insp_dist_report"),
    )
    op.create_index("ix_insp_distribution_report_tenant_id", "insp_distribution_report", ["tenant_id"])
    op.create_index("ix_insp_distribution_report_report_id", "insp_distribution_report", ["report_id"])
    op.create_index("ix_insp_distribution_report_distribution_id", "insp_distribution_report", ["distribution_id"])

    op.create_table(
        "insp_task",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_id", sa.Integer(), sa.ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=True),
        sa.Column("defect_id", sa.Integer(), sa.ForeignKey("insp_defect.id", ondelete="CASCADE"), nullable=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("insp_report.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_insp_task_tenant_id", "insp_task", ["tenant_id"])
    op.create_index("ix_insp_task_object_id", "insp_task", ["object_id"])
    op.create_index("ix_insp_task_defect_id", "insp_task", ["defect_id"])
    op.create_index("ix_insp_task_report_id", "insp_task", ["report_id"])

    op.create_table(
        "insp_invoice",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_order_id", sa.Integer(), sa.ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_cent", sa.Integer(), nullable=False),
    )
    op.create_index("ix_insp_invoice_tenant_id", "insp_invoice", ["tenant_id"])
    op.create_index("ix_insp_invoice_inspection_order_id", "insp_invoice", ["inspection_order_id"])

    op.create_table(
        "insp_portal_release",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("insp_customer.id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("released_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_insp_portal_release_tenant_id", "insp_portal_release", ["tenant_id"])
    op.create_index("ix_insp_portal_release_customer_id", "insp_portal_release", ["customer_id"])


def downgrade():
    op.drop_index("ix_insp_portal_release_customer_id", table_name="insp_portal_release")
    op.drop_index("ix_insp_portal_release_tenant_id", table_name="insp_portal_release")
    op.drop_table("insp_portal_release")

    op.drop_index("ix_insp_invoice_inspection_order_id", table_name="insp_invoice")
    op.drop_index("ix_insp_invoice_tenant_id", table_name="insp_invoice")
    op.drop_table("insp_invoice")

    op.drop_index("ix_insp_task_report_id", table_name="insp_task")
    op.drop_index("ix_insp_task_defect_id", table_name="insp_task")
    op.drop_index("ix_insp_task_object_id", table_name="insp_task")
    op.drop_index("ix_insp_task_tenant_id", table_name="insp_task")
    op.drop_table("insp_task")

    op.drop_index("ix_insp_distribution_report_distribution_id", table_name="insp_distribution_report")
    op.drop_index("ix_insp_distribution_report_report_id", table_name="insp_distribution_report")
    op.drop_index("ix_insp_distribution_report_tenant_id", table_name="insp_distribution_report")
    op.drop_table("insp_distribution_report")

    op.drop_index("ix_insp_appointment_inspection_order_id", table_name="insp_appointment")
    op.drop_index("ix_insp_appointment_tenant_id", table_name="insp_appointment")
    op.drop_table("insp_appointment")
