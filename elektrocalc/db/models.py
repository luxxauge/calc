from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Date,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base
from .enums import (
    CalcPolicy,
    ComplianceScope,
    ComplianceSeverity,
    ComplianceStatus,
    InstallType,
    PlanFileType,
    ProjectProfile,
    QuantitySource,
    RenovationDepth,
    VariantKey,
)

# -----------------------------
# CORE (stammdaten / defaults)
# -----------------------------

class CoreConfigVersion(Base):
    __tablename__ = "core_config_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # convenient relationships
    articles: Mapped[list["CoreArticle"]] = relationship(back_populates="config_version")
    templates: Mapped[list["CorePositionTemplate"]] = relationship(back_populates="config_version")


class CoreArticle(Base):
    __tablename__ = "core_article"
    __table_args__ = (
        UniqueConstraint("config_version_id", "manufacturer", "article_no", name="uq_article_manu_no_per_cfg"),
        UniqueConstraint("config_version_id", "ean", name="uq_article_ean_per_cfg"),
        Index("ix_article_lookup", "manufacturer", "article_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_version_id: Mapped[int] = mapped_column(ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False)

    manufacturer: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    article_no: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    ean: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    short_text: Mapped[str] = mapped_column(String(255), nullable=False)
    long_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="pcs")

    # money stored in cents for robustness
    ek_cent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vk_cent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    commodity_group: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    discount_group: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    config_version: Mapped["CoreConfigVersion"] = relationship(back_populates="articles")


class CorePositionTemplate(Base):
    __tablename__ = "core_position_template"
    __table_args__ = (
        UniqueConstraint("config_version_id", "code", name="uq_template_code_per_cfg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_version_id: Mapped[int] = mapped_column(ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_unit: Mapped[str] = mapped_column(String(16), nullable=False)

    # time in seconds per unit (snapshot-able later)
    time_sec_per_unit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # rounding settings
    min_qty: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)          # e.g. "1", "0.1"
    ceil_to: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)         # e.g. "1", "0.1"
    decimals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    norm_tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    config_version: Mapped["CoreConfigVersion"] = relationship(back_populates="templates")
    material_lines: Mapped[list["CoreTemplateMaterialLine"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )


class CoreTemplateMaterialLine(Base):
    __tablename__ = "core_template_material_line"
    __table_args__ = (
        UniqueConstraint("template_id", "line_no", name="uq_template_line_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("core_position_template.id", ondelete="CASCADE"), nullable=False)

    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    article_id: Mapped[int] = mapped_column(ForeignKey("core_article.id", ondelete="RESTRICT"), nullable=False)

    qty_per_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="1")  # Decimal as string
    waste_factor: Mapped[str] = mapped_column(String(32), nullable=False, default="0")  # Decimal as string

    template: Mapped["CorePositionTemplate"] = relationship(back_populates="material_lines")
    article: Mapped["CoreArticle"] = relationship()


class CoreVariantDefault(Base):
    __tablename__ = "core_variant_default"
    __table_args__ = (
        UniqueConstraint("config_version_id", "profile", "variant_key", "room_type", "item_code", name="uq_var_default"),
        Index("ix_var_default_profile_variant", "profile", "variant_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_version_id: Mapped[int] = mapped_column(ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False)

    profile: Mapped[ProjectProfile] = mapped_column(String(32), nullable=False)
    variant_key: Mapped[VariantKey] = mapped_column(String(16), nullable=False)
    room_type: Mapped[str] = mapped_column(String(64), nullable=False)
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)

    # either fixed quantity or a formula; both as strings
    qty_rule: Mapped[str] = mapped_column(String(128), nullable=False, default="0")
    min_qty: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    max_qty: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    rounding: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # e.g. "ceil:1", "round:2"


class CoreRuleParam(Base):
    __tablename__ = "core_rule_param"
    __table_args__ = (
        UniqueConstraint("config_version_id", "profile", "variant_key", "key", name="uq_rule_param"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_version_id: Mapped[int] = mapped_column(ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False)

    profile: Mapped[ProjectProfile] = mapped_column(String(32), nullable=False)
    variant_key: Mapped[VariantKey] = mapped_column(String(16), nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str] = mapped_column(String(128), nullable=False)  # Decimal/int/string as text


class CoreTextBlock(Base):
    __tablename__ = "core_text_block"
    __table_args__ = (
        UniqueConstraint("config_version_id", "key", name="uq_text_block_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_version_id: Mapped[int] = mapped_column(ForeignKey("core_config_version.id", ondelete="CASCADE"), nullable=False)

    key: Mapped[str] = mapped_column(String(64), nullable=False)     # e.g. "offer.intro"
    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # e.g. {"profile":["EFH"],"variant":["premium"]}
    content: Mapped[str] = mapped_column(Text, nullable=False)


# -----------------------------
# PROJECT (projects + plans + calcs)
# -----------------------------

class Project(Base):
    __tablename__ = "prj_project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    profile: Mapped[ProjectProfile] = mapped_column(String(32), nullable=False, default=ProjectProfile.EFH.value)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    inputs: Mapped["ProjectInputs"] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")
    plans: Mapped[list["Plan"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    calc_runs: Mapped[list["CalcRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    qty_mappings: Mapped[list["PlanQtyMapping"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectInputs(Base):
    __tablename__ = "prj_project_inputs"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_inputs_1to1"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False)

    # base geometry / type
    area_m2: Mapped[str] = mapped_column(String(32), nullable=False, default="0")
    floors: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    room_height_m: Mapped[str] = mapped_column(String(16), nullable=False, default="2.45")

    building_type: Mapped[str] = mapped_column(String(16), nullable=False, default="efh")  # efh|mfh|gewerbe
    apartments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    install_type: Mapped[InstallType] = mapped_column(String(8), nullable=False, default=InstallType.UP.value)
    renovation_depth: Mapped[RenovationDepth] = mapped_column(String(16), nullable=False, default=RenovationDepth.MEDIUM.value)

    # proxy factors
    distribution_factor: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")  # central vs decentral
    layout_factor: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")        # simple vs complex

    # residential counts
    rooms_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wc_extra: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    has_hwr: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    has_outdoor: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # kalkulationsparameter
    labor_rate_eur_h: Mapped[str] = mapped_column(String(16), nullable=False, default="72")
    overhead_pct: Mapped[str] = mapped_column(String(16), nullable=False, default="0")  # e.g. 0.15
    profit_pct: Mapped[str] = mapped_column(String(16), nullable=False, default="0")    # e.g. 0.10

    # business counts
    workplaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checkout_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    machine_feeders: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="inputs")


class PlanAsset(Base):
    __tablename__ = "prj_plan_asset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False)

    file_type: Mapped[PlanFileType] = mapped_column(String(8), nullable=False)
    original_relpath: Mapped[str] = mapped_column(String(512), nullable=False)
    original_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # rendered raster cache (per page & dpi), store as files; DB keeps relpaths
    preview_relpath: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    work_relpath: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    pdf_page_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preview_dpi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    work_dpi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Plan(Base):
    __tablename__ = "prj_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    plan_asset_id: Mapped[int] = mapped_column(ForeignKey("prj_plan_asset.id", ondelete="RESTRICT"), nullable=False)

    # scale: meters per pixel. Must be set before meter-calcs.
    scale_m_per_px: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    rotation_deg: Mapped[str] = mapped_column(String(16), nullable=False, default="0")
    origin_offset_px_x: Mapped[str] = mapped_column(String(16), nullable=False, default="0")
    origin_offset_px_y: Mapped[str] = mapped_column(String(16), nullable=False, default="0")

    project: Mapped["Project"] = relationship(back_populates="plans")
    asset: Mapped["PlanAsset"] = relationship()

    rooms: Mapped[list["PlanRoom"]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    points: Mapped[list["PlanPoint"]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    routes: Mapped[list["PlanRoute"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class PlanRoom(Base):
    __tablename__ = "prj_plan_room"
    __table_args__ = (
        Index("ix_plan_room_plan", "plan_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("prj_plan.id", ondelete="CASCADE"), nullable=False)

    room_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    polygon_px: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"points":[{"x":..,"y":..},...]}
    area_m2: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    perimeter_m: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plan: Mapped["Plan"] = relationship(back_populates="rooms")


class PlanPoint(Base):
    __tablename__ = "prj_plan_point"
    __table_args__ = (
        Index("ix_plan_point_plan", "plan_id"),
        Index("ix_plan_point_type", "point_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("prj_plan.id", ondelete="CASCADE"), nullable=False)

    point_type: Mapped[str] = mapped_column(String(64), nullable=False)  # item-code-ish e.g. SOCKET, DATA, UV
    x_px: Mapped[int] = mapped_column(Integer, nullable=False)
    y_px: Mapped[int] = mapped_column(Integer, nullable=False)

    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    plan: Mapped["Plan"] = relationship(back_populates="points")


class PlanRoute(Base):
    __tablename__ = "prj_plan_route"
    __table_args__ = (
        Index("ix_plan_route_plan", "plan_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("prj_plan.id", ondelete="CASCADE"), nullable=False)

    route_type: Mapped[str] = mapped_column(String(64), nullable=False)  # CABLE_ROUTE, TRUNKING, etc.
    polyline_px: Mapped[dict] = mapped_column(JSON, nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    plan: Mapped["Plan"] = relationship(back_populates="routes")


class VariantPolicy(Base):
    __tablename__ = "prj_variant_policy"
    __table_args__ = (
        UniqueConstraint("project_id", "variant_key", name="uq_variant_policy"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False)
    variant_key: Mapped[VariantKey] = mapped_column(String(16), nullable=False)
    policy: Mapped[CalcPolicy] = mapped_column(String(16), nullable=False, default=CalcPolicy.PROXY.value)


class CalcRun(Base):
    __tablename__ = "prj_calc_run"
    __table_args__ = (
        Index("ix_calc_run_project_variant", "project_id", "variant_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("prj_project.id", ondelete="CASCADE"), nullable=False)
    variant_key: Mapped[VariantKey] = mapped_column(String(16), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    core_config_version_id: Mapped[int] = mapped_column(ForeignKey("core_config_version.id", ondelete="RESTRICT"), nullable=False)

    # hashes to make run reproducible
    inputs_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # totals (money in cents, time in seconds)
    total_material_ek_cent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_labor_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_net_cent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_vat_cent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_gross_cent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # store calculation pipeline parameters snapshot
    calc_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    project: Mapped["Project"] = relationship(back_populates="calc_runs")
    quantities: Mapped[list["CalcRunQuantity"]] = relationship(back_populates="calc_run", cascade="all, delete-orphan")
    positions: Mapped[list["CalcRunPosition"]] = relationship(back_populates="calc_run", cascade="all, delete-orphan")
    materials: Mapped[list["CalcRunMaterialSnapshot"]] = relationship(back_populates="calc_run", cascade="all, delete-orphan")
    compliance: Mapped[list["ComplianceFinding"]] = relationship(back_populates="calc_run", cascade="all, delete-orphan")


class CalcRunQuantity(Base):
    __tablename__ = "prj_calc_run_qty"
    __table_args__ = (
        Index("ix_calc_qty_run_item", "calc_run_id", "item_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calc_run_id: Mapped[int] = mapped_column(ForeignKey("prj_calc_run.id", ondelete="CASCADE"), nullable=False)

    room_ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # e.g. plan_room_id or derived room key
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    qty: Mapped[str] = mapped_column(String(32), nullable=False)  # Decimal as string
    unit: Mapped[str] = mapped_column(String(16), nullable=False)

    source: Mapped[QuantitySource] = mapped_column(String(24), nullable=False, default=QuantitySource.DEFAULTS.value)

    calc_run: Mapped["CalcRun"] = relationship(back_populates="quantities")


class CalcRunPosition(Base):
    __tablename__ = "prj_calc_run_position"
    __table_args__ = (
        Index("ix_calc_pos_run", "calc_run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calc_run_id: Mapped[int] = mapped_column(ForeignKey("prj_calc_run.id", ondelete="CASCADE"), nullable=False)

    pos_no: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    short_text: Mapped[str] = mapped_column(String(255), nullable=False)
    long_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    qty: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)

    # snapshots for pricing/time
    template_code_snapshot: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    time_sec_per_unit_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    material_ek_cent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    labor_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    net_cent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    calc_run: Mapped["CalcRun"] = relationship(back_populates="positions")


class CalcRunMaterialSnapshot(Base):
    __tablename__ = "prj_calc_run_material"
    __table_args__ = (
        Index("ix_calc_mat_run", "calc_run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calc_run_id: Mapped[int] = mapped_column(ForeignKey("prj_calc_run.id", ondelete="CASCADE"), nullable=False)

    article_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # may be null if ad-hoc material
    article_label_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)

    qty: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)

    ek_cent_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    calc_run: Mapped["CalcRun"] = relationship(back_populates="materials")


class ComplianceFinding(Base):
    __tablename__ = "prj_compliance_finding"
    __table_args__ = (
        Index("ix_compliance_run", "calc_run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calc_run_id: Mapped[int] = mapped_column(ForeignKey("prj_calc_run.id", ondelete="CASCADE"), nullable=False)

    scope: Mapped[ComplianceScope] = mapped_column(String(32), nullable=False)
    severity: Mapped[ComplianceSeverity] = mapped_column(String(32), nullable=False)
    status: Mapped[ComplianceStatus] = mapped_column(String(32), nullable=False, default=ComplianceStatus.OPEN.value)

    key: Mapped[str] = mapped_column(String(64), nullable=False)  # stable key for rule
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    calc_run: Mapped["CalcRun"] = relationship(back_populates="compliance")

# -----------------------------
# Catalog / Articles (v1.1)
# -----------------------------

class Item(Base):
    __tablename__ = "item"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_no: Mapped[str] = mapped_column(String(64), index=True)   # your internal/no.
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    unit: Mapped[str] = mapped_column(String(32), default="pcs")
    vat_rate: Mapped[str] = mapped_column(String(16), default="0.19")  # decimal string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("article_no", "manufacturer", name="uq_item_article_manufacturer"),
    )

class ItemPrice(Base):
    __tablename__ = "item_price"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id", ondelete="CASCADE"), index=True)
    price_ek_cent: Mapped[int] = mapped_column(Integer, default=0)
    price_vk_cent: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    item: Mapped["Item"] = relationship("Item")

# Import tracking (optional but useful for auditability)
class ImportBatch(Base):
    __tablename__ = "import_batch"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # e.g., "items_excel"
    filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

# -----------------------------
# LV / Ausschreibung (v1.2)
# -----------------------------

class LvDocument(Base):
    __tablename__ = "lv_document"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(16), default="xlsx")  # xlsx|csv|txt
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    positions: Mapped[list["LvPosition"]] = relationship("LvPosition", back_populates="document", cascade="all, delete-orphan")

class LvPosition(Base):
    __tablename__ = "lv_position"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lv_document_id: Mapped[int] = mapped_column(ForeignKey("lv_document.id", ondelete="CASCADE"), index=True)
    pos_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    short_text: Mapped[str] = mapped_column(String(255))
    long_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qty: Mapped[str] = mapped_column(String(32), default="1")
    unit: Mapped[str] = mapped_column(String(32), default="pcs")
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)

    document: Mapped["LvDocument"] = relationship("LvDocument", back_populates="positions")
    match: Mapped[Optional["LvPositionMatch"]] = relationship("LvPositionMatch", back_populates="position", uselist=False, cascade="all, delete-orphan")

class LvPositionMatch(Base):
    __tablename__ = "lv_position_match"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lv_position_id: Mapped[int] = mapped_column(ForeignKey("lv_position.id", ondelete="CASCADE"), unique=True, index=True)
    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("item.id", ondelete="SET NULL"), index=True, nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # "manual"|"auto"
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    position: Mapped["LvPosition"] = relationship("LvPosition", back_populates="match")
    item: Mapped[Optional["Item"]] = relationship("Item")

# -----------------------------
# Kalkulation (v1.3)
# -----------------------------

class CalcEstimate(Base):
    __tablename__ = "calc_estimate"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lv_document_id: Mapped[int] = mapped_column(ForeignKey("lv_document.id", ondelete="CASCADE"), index=True)
    variant: Mapped[str] = mapped_column(String(16))  # standard|komfort|premium
    labor_rate_cent: Mapped[int] = mapped_column(Integer, default=6500)  # €/h *100
    overhead_pct: Mapped[str] = mapped_column(String(16), default="0.15")  # decimal string
    profit_pct: Mapped[str] = mapped_column(String(16), default="0.10")    # decimal string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lines: Mapped[list["CalcEstimateLine"]] = relationship("CalcEstimateLine", back_populates="estimate", cascade="all, delete-orphan")

class CalcEstimateLine(Base):
    __tablename__ = "calc_estimate_line"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("calc_estimate.id", ondelete="CASCADE"), index=True)
    lv_position_id: Mapped[int] = mapped_column(ForeignKey("lv_position.id", ondelete="CASCADE"), index=True)

    qty: Mapped[str] = mapped_column(String(32), default="1")
    unit: Mapped[str] = mapped_column(String(32), default="pcs")

    material_cent: Mapped[int] = mapped_column(Integer, default=0)  # VK total for this line (net)
    labor_minutes: Mapped[int] = mapped_column(Integer, default=0)
    labor_cent: Mapped[int] = mapped_column(Integer, default=0)     # labor total (net)
    total_cent: Mapped[int] = mapped_column(Integer, default=0)
    labor_source: Mapped[str] = mapped_column(String(16), default="heuristic")  # rule|heuristic
    labor_task_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    labor_rule_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    estimate: Mapped["CalcEstimate"] = relationship("CalcEstimate", back_populates="lines")
    position: Mapped["LvPosition"] = relationship("LvPosition")

# -----------------------------
# Zeitkatalog / Regeln (v1.4)
# -----------------------------

class LaborTask(Base):
    __tablename__ = "labor_task"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(32), default="pcs")  # pcs|m|m²|h|...
    minutes_per_unit: Mapped[int] = mapped_column(Integer, default=10)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LaborRule(Base):
    __tablename__ = "labor_rule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern: Mapped[str] = mapped_column(String(255))  # substring or regex
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)  # lower first
    task_id: Mapped[int] = mapped_column(ForeignKey("labor_task.id", ondelete="CASCADE"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["LaborTask"] = relationship("LaborTask")

# -----------------------------
# Variantenpakete (DIN 18015) – v1.6
# -----------------------------

class VariantProfile(Base):
    __tablename__ = "variant_profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # standard|komfort|premium
    name: Mapped[str] = mapped_column(String(64))
    # Default Zuschläge (können pro Kalkulationslauf überschrieben werden)
    default_overhead_pct: Mapped[str] = mapped_column(String(16), default="0.15")
    default_profit_pct: Mapped[str] = mapped_column(String(16), default="0.10")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rules: Mapped[list["VariantRule"]] = relationship("VariantRule", back_populates="profile", cascade="all, delete-orphan")

class VariantRule(Base):
    __tablename__ = "variant_rule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_profile_id: Mapped[int] = mapped_column(ForeignKey("variant_profile.id", ondelete="CASCADE"), index=True)
    # Matching: entweder Task-Code (aus Zeitkatalog) oder Pattern auf LV-Text
    match_task_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    match_pattern: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Adjustments
    labor_multiplier: Mapped[str] = mapped_column(String(16), default="1.00")     # e.g. 1.10
    material_multiplier: Mapped[str] = mapped_column(String(16), default="1.00")  # e.g. 1.05
    add_labor_minutes: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    profile: Mapped["VariantProfile"] = relationship("VariantProfile", back_populates="rules")

class CalcExtraLine(Base):
    __tablename__ = "calc_extra_line"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("calc_estimate.id", ondelete="CASCADE"), index=True)

    description: Mapped[str] = mapped_column(String(255))
    qty: Mapped[str] = mapped_column(String(32), default="1")
    unit: Mapped[str] = mapped_column(String(32), default="pcs")

    material_cent: Mapped[int] = mapped_column(Integer, default=0)
    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("item.id"), nullable=True)
    labor_minutes: Mapped[int] = mapped_column(Integer, default=0)
    labor_cent: Mapped[int] = mapped_column(Integer, default=0)
    total_cent: Mapped[int] = mapped_column(Integer, default=0)

    source: Mapped[str] = mapped_column(String(32), default="variant_param")  # variant_param|manual|other
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    estimate: Mapped["CalcEstimate"] = relationship("CalcEstimate")
    item: Mapped[Optional["Item"]] = relationship("Item")

# -----------------------------
# Rate Card / Preisblatt (v1.8)
# -----------------------------

class RateCard(Base):
    __tablename__ = "rate_card"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lines: Mapped[list["RateCardLine"]] = relationship("RateCardLine", back_populates="card", cascade="all, delete-orphan")

class RateCardLine(Base):
    __tablename__ = "rate_card_line"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rate_card_id: Mapped[int] = mapped_column(ForeignKey("rate_card.id", ondelete="CASCADE"), index=True)

    key: Mapped[str] = mapped_column(String(64), index=True)  # e.g. socket_std, data_pre
    description: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(32), default="pcs")
    material_unit_cent: Mapped[int] = mapped_column(Integer, default=0)  # VK material per unit (net)
    labor_task_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # optional: map to an Item (then material_unit_cent can be auto-derived if desired)
    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("item.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    card: Mapped["RateCard"] = relationship("RateCard", back_populates="lines")
    item: Mapped[Optional["Item"]] = relationship("Item")

# -----------------------------
# Parametrische Regeln (v1.9)
# -----------------------------

class ParamRule(Base):
    __tablename__ = "param_rule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Scope
    variant_key: Mapped[str] = mapped_column(String(32), default="komfort")  # standard|komfort|premium|any
    building_type: Mapped[str] = mapped_column(String(16), default="any")    # efh|mfh|gewerbe|any

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)

    # Output: which rate-card line to use
    rate_key: Mapped[str] = mapped_column(String(64))  # e.g. socket_kom
    description_tpl: Mapped[str] = mapped_column(String(255), default="{rate_key} (param)")
    unit: Mapped[str] = mapped_column(String(32), default="pcs")

    # Qty expression (safe eval): allowed vars: area_m2, rooms, floors, apartments
    qty_expr: Mapped[str] = mapped_column(String(255), default="0")

    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
# -----------------------------
# Plan -> Calculation Mapping
# -----------------------------
class PlanQtyMapping(Base):
    __tablename__ = "prj_plan_qty_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("prj_project.id"), nullable=False, index=True)

    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # "route" or "point"
    key: Mapped[str] = mapped_column(String(64), nullable=False)   # route_type or point_type
    variant_key: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # optional override per variant

    rate_key: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="St")
    qty_factor: Mapped[str] = mapped_column(String(16), nullable=False, default="1")  # multiplicator (e.g. Verteiler-/Weg-Faktor)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="qty_mappings")


# -----------------------------
# Mandantenfähige Prüfsoftware (MVP-1 Fundament)
# -----------------------------

class InspTenant(Base):
    __tablename__ = "insp_tenant"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InspCustomer(Base):
    __tablename__ = "insp_customer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InspSite(Base):
    __tablename__ = "insp_site"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("insp_customer.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class InspObject(Base):
    __tablename__ = "insp_object"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("insp_customer.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("insp_site.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class InspDistribution(Base):
    __tablename__ = "insp_distribution"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)


class InspInspectionOrder(Base):
    __tablename__ = "insp_inspection_order"
    __table_args__ = (
        CheckConstraint("status in ('draft','planned','in_progress','technical_done','finalized','archived')", name="ck_insp_order_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InspInspectionOrderDistribution(Base):
    __tablename__ = "insp_inspection_order_distribution"
    __table_args__ = (
        UniqueConstraint("inspection_order_id", "distribution_id", name="uq_insp_order_distribution"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_order_id: Mapped[int] = mapped_column(ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False, index=True)
    distribution_id: Mapped[int] = mapped_column(ForeignKey("insp_distribution.id", ondelete="CASCADE"), nullable=False, index=True)


class InspAppointment(Base):
    __tablename__ = "insp_appointment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_order_id: Mapped[int] = mapped_column(ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class InspMeasurementSet(Base):
    __tablename__ = "insp_measurement_set"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_order_id: Mapped[int] = mapped_column(ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)


class InspMeasurement(Base):
    __tablename__ = "insp_measurement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    measurement_set_id: Mapped[int] = mapped_column(ForeignKey("insp_measurement_set.id", ondelete="CASCADE"), nullable=False, index=True)
    point_label: Mapped[str] = mapped_column(String(120), nullable=False)
    measured_value: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="")


class InspDefect(Base):
    __tablename__ = "insp_defect"
    __table_args__ = (
        CheckConstraint("status in ('open','assessed','deadline_set','follow_up','rechecked','closed')", name="ck_insp_defect_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_order_id: Mapped[int] = mapped_column(ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class InspReport(Base):
    __tablename__ = "insp_report"
    __table_args__ = (
        CheckConstraint("status in ('draft','for_approval','approved','finalized','published','archived')", name="ck_insp_report_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_order_id: Mapped[int] = mapped_column(ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")


class InspDistributionReport(Base):
    __tablename__ = "insp_distribution_report"
    __table_args__ = (
        UniqueConstraint("report_id", "distribution_id", name="uq_insp_dist_report"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("insp_report.id", ondelete="CASCADE"), nullable=False, index=True)
    distribution_id: Mapped[int] = mapped_column(ForeignKey("insp_distribution.id", ondelete="CASCADE"), nullable=False, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class InspTask(Base):
    __tablename__ = "insp_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id: Mapped[Optional[int]] = mapped_column(ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=True, index=True)
    defect_id: Mapped[Optional[int]] = mapped_column(ForeignKey("insp_defect.id", ondelete="CASCADE"), nullable=True, index=True)
    report_id: Mapped[Optional[int]] = mapped_column(ForeignKey("insp_report.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")


class InspInvoice(Base):
    __tablename__ = "insp_invoice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_order_id: Mapped[int] = mapped_column(ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    total_cent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class InspPortalRelease(Base):
    __tablename__ = "insp_portal_release"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("insp_customer.id", ondelete="CASCADE"), nullable=False, index=True)
    release_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    released_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InspMeasuringDevice(Base):
    __tablename__ = "insp_measuring_device"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    serial_no: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    calibration_due: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class InspDocument(Base):
    __tablename__ = "insp_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id: Mapped[Optional[int]] = mapped_column(ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=True, index=True)
    inspection_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("insp_inspection_order.id", ondelete="CASCADE"), nullable=True, index=True)
    defect_id: Mapped[Optional[int]] = mapped_column(ForeignKey("insp_defect.id", ondelete="CASCADE"), nullable=True, index=True)
    report_id: Mapped[Optional[int]] = mapped_column(ForeignKey("insp_report.id", ondelete="CASCADE"), nullable=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InspCommunicationEntry(Base):
    __tablename__ = "insp_communication_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("insp_task.id", ondelete="CASCADE"), nullable=True, index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("insp_customer.id", ondelete="CASCADE"), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="internal")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InspAuditLog(Base):
    __tablename__ = "insp_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    actor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InspDefectDeadline(Base):
    __tablename__ = "insp_defect_deadline"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("insp_defect.id", ondelete="CASCADE"), nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InspApprovalStep(Base):
    __tablename__ = "insp_approval_step"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # report|invoice|inspection_order
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    required_role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class InspNotification(Base):
    __tablename__ = "insp_notification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    related_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class InspInspectionCycle(Base):
    __tablename__ = "insp_inspection_cycle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("insp_object.id", ondelete="CASCADE"), nullable=False, index=True)
    interval_months: Mapped[int] = mapped_column(Integer, nullable=False, default=48)
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class InspBackupRun(Base):
    __tablename__ = "insp_backup_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("insp_tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
