"""inspection next six modules

Revision ID: 0017inspectionnext6
Revises: 0016inspectiongovops
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0017inspectionnext6"
down_revision = "0016inspectiongovops"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "insp_thermography_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_id", sa.Integer(), sa.ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=False),
        sa.Column("defect_id", sa.Integer(), sa.ForeignKey("insp_defect.id", ondelete="CASCADE"), nullable=True),
        sa.Column("image_ref", sa.String(length=255), nullable=False),
        sa.Column("max_temp_c", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_insp_thermography_entry_tenant_id", "insp_thermography_entry", ["tenant_id"])
    op.create_index("ix_insp_thermography_entry_object_id", "insp_thermography_entry", ["object_id"])
    op.create_index("ix_insp_thermography_entry_defect_id", "insp_thermography_entry", ["defect_id"])

    op.create_table(
        "insp_device_calibration",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("measuring_device_id", sa.Integer(), sa.ForeignKey("insp_measuring_device.id", ondelete="CASCADE"), nullable=False),
        sa.Column("calibrated_at", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("certificate_ref", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_insp_device_calibration_tenant_id", "insp_device_calibration", ["tenant_id"])
    op.create_index("ix_insp_device_calibration_measuring_device_id", "insp_device_calibration", ["measuring_device_id"])

    op.create_table(
        "insp_number_sequence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False),
        sa.UniqueConstraint("tenant_id", "scope", name="uq_insp_number_sequence_scope"),
    )
    op.create_index("ix_insp_number_sequence_tenant_id", "insp_number_sequence", ["tenant_id"])

    op.create_table(
        "insp_payment_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("insp_invoice.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount_cent", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("booked_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_insp_payment_entry_tenant_id", "insp_payment_entry", ["tenant_id"])
    op.create_index("ix_insp_payment_entry_invoice_id", "insp_payment_entry", ["invoice_id"])

    op.create_table(
        "insp_data_retention_rule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_type", sa.String(length=64), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("delete_mode", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_insp_data_retention_rule_tenant_id", "insp_data_retention_rule", ["tenant_id"])

    op.create_table(
        "insp_restore_test",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("backup_run_id", sa.Integer(), sa.ForeignKey("insp_backup_run.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("tested_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_insp_restore_test_tenant_id", "insp_restore_test", ["tenant_id"])
    op.create_index("ix_insp_restore_test_backup_run_id", "insp_restore_test", ["backup_run_id"])


def downgrade():
    op.drop_index("ix_insp_restore_test_backup_run_id", table_name="insp_restore_test")
    op.drop_index("ix_insp_restore_test_tenant_id", table_name="insp_restore_test")
    op.drop_table("insp_restore_test")

    op.drop_index("ix_insp_data_retention_rule_tenant_id", table_name="insp_data_retention_rule")
    op.drop_table("insp_data_retention_rule")

    op.drop_index("ix_insp_payment_entry_invoice_id", table_name="insp_payment_entry")
    op.drop_index("ix_insp_payment_entry_tenant_id", table_name="insp_payment_entry")
    op.drop_table("insp_payment_entry")

    op.drop_index("ix_insp_number_sequence_tenant_id", table_name="insp_number_sequence")
    op.drop_table("insp_number_sequence")

    op.drop_index("ix_insp_device_calibration_measuring_device_id", table_name="insp_device_calibration")
    op.drop_index("ix_insp_device_calibration_tenant_id", table_name="insp_device_calibration")
    op.drop_table("insp_device_calibration")

    op.drop_index("ix_insp_thermography_entry_defect_id", table_name="insp_thermography_entry")
    op.drop_index("ix_insp_thermography_entry_object_id", table_name="insp_thermography_entry")
    op.drop_index("ix_insp_thermography_entry_tenant_id", table_name="insp_thermography_entry")
    op.drop_table("insp_thermography_entry")
