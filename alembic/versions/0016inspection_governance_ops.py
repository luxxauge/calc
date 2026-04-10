"""inspection governance and operations modules

Revision ID: 0016inspectiongovops
Revises: 0015inspectionsupport
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0016inspectiongovops"
down_revision = "0015inspectionsupport"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "insp_defect_deadline",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("defect_id", sa.Integer(), sa.ForeignKey("insp_defect.id", ondelete="CASCADE"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_insp_defect_deadline_tenant_id", "insp_defect_deadline", ["tenant_id"])
    op.create_index("ix_insp_defect_deadline_defect_id", "insp_defect_deadline", ["defect_id"])

    op.create_table(
        "insp_approval_step",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("required_role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_insp_approval_step_tenant_id", "insp_approval_step", ["tenant_id"])

    op.create_table(
        "insp_notification",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("related_type", sa.String(length=32), nullable=True),
        sa.Column("related_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_insp_notification_tenant_id", "insp_notification", ["tenant_id"])

    op.create_table(
        "insp_inspection_cycle",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("object_id", sa.Integer(), sa.ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interval_months", sa.Integer(), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_insp_inspection_cycle_tenant_id", "insp_inspection_cycle", ["tenant_id"])
    op.create_index("ix_insp_inspection_cycle_object_id", "insp_inspection_cycle", ["object_id"])

    op.create_table(
        "insp_backup_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_insp_backup_run_tenant_id", "insp_backup_run", ["tenant_id"])


def downgrade():
    op.drop_index("ix_insp_backup_run_tenant_id", table_name="insp_backup_run")
    op.drop_table("insp_backup_run")

    op.drop_index("ix_insp_inspection_cycle_object_id", table_name="insp_inspection_cycle")
    op.drop_index("ix_insp_inspection_cycle_tenant_id", table_name="insp_inspection_cycle")
    op.drop_table("insp_inspection_cycle")

    op.drop_index("ix_insp_notification_tenant_id", table_name="insp_notification")
    op.drop_table("insp_notification")

    op.drop_index("ix_insp_approval_step_tenant_id", table_name="insp_approval_step")
    op.drop_table("insp_approval_step")

    op.drop_index("ix_insp_defect_deadline_defect_id", table_name="insp_defect_deadline")
    op.drop_index("ix_insp_defect_deadline_tenant_id", table_name="insp_defect_deadline")
    op.drop_table("insp_defect_deadline")
