"""schema v1

Revision ID: 0001
Revises: 
Create Date: 2026-01-29

"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Core
    op.create_table(
        "core_config_version",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "core_article",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_version_id", sa.Integer(), sa.ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False),
        sa.Column("manufacturer", sa.String(length=120), nullable=True),
        sa.Column("article_no", sa.String(length=120), nullable=True),
        sa.Column("ean", sa.String(length=32), nullable=True),
        sa.Column("short_text", sa.String(length=255), nullable=False),
        sa.Column("long_text", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=16), nullable=False, server_default="pcs"),
        sa.Column("ek_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vk_cent", sa.Integer(), nullable=True),
        sa.Column("commodity_group", sa.String(length=64), nullable=True),
        sa.Column("discount_group", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_article_lookup", "core_article", ["manufacturer", "article_no"])
    op.create_index("uq_article_manu_no_per_cfg", "core_article", ["config_version_id", "manufacturer", "article_no"], unique=True)
    op.create_index("uq_article_ean_per_cfg", "core_article", ["config_version_id", "ean"], unique=True)

    op.create_table(
        "core_position_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_version_id", sa.Integer(), sa.ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("default_unit", sa.String(length=16), nullable=False),
        sa.Column("time_sec_per_unit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_qty", sa.String(length=32), nullable=True),
        sa.Column("ceil_to", sa.String(length=32), nullable=True),
        sa.Column("decimals", sa.Integer(), nullable=True),
        sa.Column("norm_tags", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("uq_template_code_per_cfg", "core_position_template", ["config_version_id", "code"], unique=True)

    op.create_table(
        "core_template_material_line",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("core_position_template.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("core_article.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("qty_per_unit", sa.String(length=32), nullable=False, server_default="1"),
        sa.Column("waste_factor", sa.String(length=32), nullable=False, server_default="0"),
    )
    op.create_index("uq_template_line_no", "core_template_material_line", ["template_id", "line_no"], unique=True)

    op.create_table(
        "core_variant_default",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_version_id", sa.Integer(), sa.ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile", sa.String(length=32), nullable=False),
        sa.Column("variant_key", sa.String(length=16), nullable=False),
        sa.Column("room_type", sa.String(length=64), nullable=False),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("qty_rule", sa.String(length=128), nullable=False, server_default="0"),
        sa.Column("min_qty", sa.String(length=32), nullable=True),
        sa.Column("max_qty", sa.String(length=32), nullable=True),
        sa.Column("rounding", sa.String(length=32), nullable=True),
    )
    op.create_index("uq_var_default", "core_variant_default", ["config_version_id","profile","variant_key","room_type","item_code"], unique=True)
    op.create_index("ix_var_default_profile_variant", "core_variant_default", ["profile","variant_key"])

    op.create_table(
        "core_rule_param",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_version_id", sa.Integer(), sa.ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile", sa.String(length=32), nullable=False),
        sa.Column("variant_key", sa.String(length=16), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=128), nullable=False),
    )
    op.create_index("uq_rule_param", "core_rule_param", ["config_version_id","profile","variant_key","key"], unique=True)

    op.create_table(
        "core_text_block",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("config_version_id", sa.Integer(), sa.ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("content", sa.Text(), nullable=False),
    )
    op.create_index("uq_text_block_key", "core_text_block", ["config_version_id","key"], unique=True)

    # Project
    op.create_table(
        "prj_project",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("profile", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "prj_project_inputs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("area_m2", sa.String(length=32), nullable=False, server_default="0"),
        sa.Column("floors", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("room_height_m", sa.String(length=16), nullable=False, server_default="2.45"),
        sa.Column("install_type", sa.String(length=8), nullable=False),
        sa.Column("renovation_depth", sa.String(length=16), nullable=False),
        sa.Column("distribution_factor", sa.String(length=16), nullable=False, server_default="1.0"),
        sa.Column("layout_factor", sa.String(length=16), nullable=False, server_default="1.0"),
        sa.Column("rooms_total", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("wc_extra", sa.Integer(), nullable=True),
        sa.Column("has_hwr", sa.Boolean(), nullable=True),
        sa.Column("has_outdoor", sa.Boolean(), nullable=True),
        sa.Column("workplaces", sa.Integer(), nullable=True),
        sa.Column("checkout_points", sa.Integer(), nullable=True),
        sa.Column("machine_feeders", sa.Integer(), nullable=True),
    )
    op.create_index("uq_project_inputs_1to1", "prj_project_inputs", ["project_id"], unique=True)

    op.create_table(
        "prj_plan_asset",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_type", sa.String(length=8), nullable=False),
        sa.Column("original_relpath", sa.String(length=512), nullable=False),
        sa.Column("original_hash", sa.String(length=64), nullable=False),
        sa.Column("preview_relpath", sa.String(length=512), nullable=True),
        sa.Column("work_relpath", sa.String(length=512), nullable=True),
        sa.Column("pdf_page_index", sa.Integer(), nullable=True),
        sa.Column("preview_dpi", sa.Integer(), nullable=True),
        sa.Column("work_dpi", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "prj_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("plan_asset_id", sa.Integer(), sa.ForeignKey("prj_plan_asset.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scale_m_per_px", sa.String(length=32), nullable=True),
        sa.Column("rotation_deg", sa.String(length=16), nullable=False, server_default="0"),
        sa.Column("origin_offset_px_x", sa.String(length=16), nullable=False, server_default="0"),
        sa.Column("origin_offset_px_y", sa.String(length=16), nullable=False, server_default="0"),
    )

    op.create_table(
        "prj_plan_room",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("prj_plan.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("polygon_px", sa.JSON(), nullable=False),
        sa.Column("area_m2", sa.String(length=32), nullable=True),
        sa.Column("perimeter_m", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_plan_room_plan", "prj_plan_room", ["plan_id"])

    op.create_table(
        "prj_plan_point",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("prj_plan.id", ondelete="CASCADE"), nullable=False),
        sa.Column("point_type", sa.String(length=64), nullable=False),
        sa.Column("x_px", sa.Integer(), nullable=False),
        sa.Column("y_px", sa.Integer(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_plan_point_plan", "prj_plan_point", ["plan_id"])
    op.create_index("ix_plan_point_type", "prj_plan_point", ["point_type"])

    op.create_table(
        "prj_plan_route",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("prj_plan.id", ondelete="CASCADE"), nullable=False),
        sa.Column("route_type", sa.String(length=64), nullable=False),
        sa.Column("polyline_px", sa.JSON(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_plan_route_plan", "prj_plan_route", ["plan_id"])

    op.create_table(
        "prj_variant_policy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_key", sa.String(length=16), nullable=False),
        sa.Column("policy", sa.String(length=16), nullable=False),
    )
    op.create_index("uq_variant_policy", "prj_variant_policy", ["project_id","variant_key"], unique=True)

    op.create_table(
        "prj_calc_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_key", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("core_config_version_id", sa.Integer(), sa.ForeignKey("core_config_version.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("inputs_hash", sa.String(length=64), nullable=False),
        sa.Column("plan_hash", sa.String(length=64), nullable=True),
        sa.Column("total_material_ek_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_labor_sec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_net_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_vat_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_gross_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calc_params", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_calc_run_project_variant", "prj_calc_run", ["project_id","variant_key"])

    op.create_table(
        "prj_calc_run_qty",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("calc_run_id", sa.Integer(), sa.ForeignKey("prj_calc_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_ref", sa.String(length=64), nullable=True),
        sa.Column("item_code", sa.String(length=64), nullable=False),
        sa.Column("qty", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
    )
    op.create_index("ix_calc_qty_run_item", "prj_calc_run_qty", ["calc_run_id","item_code"])

    op.create_table(
        "prj_calc_run_position",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("calc_run_id", sa.Integer(), sa.ForeignKey("prj_calc_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pos_no", sa.String(length=32), nullable=True),
        sa.Column("short_text", sa.String(length=255), nullable=False),
        sa.Column("long_text", sa.Text(), nullable=True),
        sa.Column("qty", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("template_code_snapshot", sa.String(length=64), nullable=True),
        sa.Column("time_sec_per_unit_snapshot", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("material_ek_cent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("labor_sec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("net_cent", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_calc_pos_run", "prj_calc_run_position", ["calc_run_id"])

    op.create_table(
        "prj_calc_run_material",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("calc_run_id", sa.Integer(), sa.ForeignKey("prj_calc_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("article_label_snapshot", sa.String(length=255), nullable=False),
        sa.Column("qty", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("ek_cent_snapshot", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_calc_mat_run", "prj_calc_run_material", ["calc_run_id"])

    op.create_table(
        "prj_compliance_finding",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("calc_run_id", sa.Integer(), sa.ForeignKey("prj_calc_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
    )
    op.create_index("ix_compliance_run", "prj_compliance_finding", ["calc_run_id"])


def downgrade() -> None:
    # drop in reverse order
    op.drop_index("ix_compliance_run", table_name="prj_compliance_finding")
    op.drop_table("prj_compliance_finding")

    op.drop_index("ix_calc_mat_run", table_name="prj_calc_run_material")
    op.drop_table("prj_calc_run_material")

    op.drop_index("ix_calc_pos_run", table_name="prj_calc_run_position")
    op.drop_table("prj_calc_run_position")

    op.drop_index("ix_calc_qty_run_item", table_name="prj_calc_run_qty")
    op.drop_table("prj_calc_run_qty")

    op.drop_index("ix_calc_run_project_variant", table_name="prj_calc_run")
    op.drop_table("prj_calc_run")

    op.drop_table("prj_variant_policy")

    op.drop_index("ix_plan_route_plan", table_name="prj_plan_route")
    op.drop_table("prj_plan_route")

    op.drop_index("ix_plan_point_type", table_name="prj_plan_point")
    op.drop_index("ix_plan_point_plan", table_name="prj_plan_point")
    op.drop_table("prj_plan_point")

    op.drop_index("ix_plan_room_plan", table_name="prj_plan_room")
    op.drop_table("prj_plan_room")

    op.drop_table("prj_plan")
    op.drop_table("prj_plan_asset")
    op.drop_table("prj_project_inputs")
    op.drop_table("prj_project")

    op.drop_table("core_text_block")
    op.drop_table("core_rule_param")
    op.drop_index("ix_var_default_profile_variant", table_name="core_variant_default")
    op.drop_table("core_variant_default")
    op.drop_table("core_template_material_line")
    op.drop_table("core_position_template")

    op.drop_index("uq_article_ean_per_cfg", table_name="core_article")
    op.drop_index("uq_article_manu_no_per_cfg", table_name="core_article")
    op.drop_index("ix_article_lookup", table_name="core_article")
    op.drop_table("core_article")

    op.drop_table("core_config_version")
