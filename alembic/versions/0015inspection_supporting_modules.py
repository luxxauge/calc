"""inspection supporting modules

Revision ID: 0015inspectionsupport
Revises: 0014inspectionopstables
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0015inspectionsupport"
down_revision = "0014inspectionopstables"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "insp_measuring_device",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("serial_no", sa.String(length=120), nullable=True),
        sa.Column("calibration_due", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_insp_measuring_device_tenant_id", "insp_measuring_device", ["tenant_id"])

    op.create_table(
        "insp_document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_id", sa.Integer(), sa.ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=True),
        sa.Column("inspection_order_id", sa.Integer(), sa.ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=True),
        sa.Column("defect_id", sa.Integer(), sa.ForeignKey("insp_defect.id", ondelete="CASCADE"), nullable=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("insp_report.id", ondelete="CASCADE"), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_insp_document_tenant_id", "insp_document", ["tenant_id"])
    op.create_index("ix_insp_document_object_id", "insp_document", ["object_id"])
    op.create_index("ix_insp_document_inspection_order_id", "insp_document", ["inspection_order_id"])
    op.create_index("ix_insp_document_defect_id", "insp_document", ["defect_id"])
    op.create_index("ix_insp_document_report_id", "insp_document", ["report_id"])

    op.create_table(
        "insp_communication_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("insp_task.id", ondelete="CASCADE"), nullable=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("insp_customer.id", ondelete="CASCADE"), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_insp_communication_entry_tenant_id", "insp_communication_entry", ["tenant_id"])
    op.create_index("ix_insp_communication_entry_task_id", "insp_communication_entry", ["task_id"])
    op.create_index("ix_insp_communication_entry_customer_id", "insp_communication_entry", ["customer_id"])

    op.create_table(
        "insp_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_insp_audit_log_tenant_id", "insp_audit_log", ["tenant_id"])


def downgrade():
    op.drop_index("ix_insp_audit_log_tenant_id", table_name="insp_audit_log")
    op.drop_table("insp_audit_log")

    op.drop_index("ix_insp_communication_entry_customer_id", table_name="insp_communication_entry")
    op.drop_index("ix_insp_communication_entry_task_id", table_name="insp_communication_entry")
    op.drop_index("ix_insp_communication_entry_tenant_id", table_name="insp_communication_entry")
    op.drop_table("insp_communication_entry")

    op.drop_index("ix_insp_document_report_id", table_name="insp_document")
    op.drop_index("ix_insp_document_defect_id", table_name="insp_document")
    op.drop_index("ix_insp_document_inspection_order_id", table_name="insp_document")
    op.drop_index("ix_insp_document_object_id", table_name="insp_document")
    op.drop_index("ix_insp_document_tenant_id", table_name="insp_document")
    op.drop_table("insp_document")

    op.drop_index("ix_insp_measuring_device_tenant_id", table_name="insp_measuring_device")
    op.drop_table("insp_measuring_device")
