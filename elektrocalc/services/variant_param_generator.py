from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from elektrocalc.db.models import ProjectInputs, LaborTask, RateCardLine, ParamRule
from elektrocalc.services.rate_card import lookup_line
from elektrocalc.services.safe_eval import safe_eval

def _d(v: Any, default: Decimal = Decimal("0")) -> Decimal:
    if v is None:
        return default
    s = str(v).strip().replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return default

@dataclass
class ExtraSpec:
    description: str
    qty: Decimal
    unit: str
    material_unit_cent: int
    labor_task_code: str
    rate_key: str
    item_id: int | None = None
    note: str | None = None

# Very conservative starter unit-material assumptions (can be replaced by mapping to real items later)
MATERIAL_RATES_CENT = {

    "socket_std": 900,     # 9 €
    "socket_kom": 1400,    # 14 €
    "socket_pre": 2200,    # 22 €
    "data_std": 1800,      # 18 €
    "data_kom": 2400,      # 24 €
    "data_pre": 3200,      # 32 €
}

def _rooms_guess(area_m2: Decimal, rooms_total: int | None) -> int:
    if rooms_total and rooms_total > 0:
        return int(rooms_total)
    # ~20m² per room as rough proxy, clamp
    if area_m2 <= 0:
        return 4
    return max(2, min(20, int((area_m2 / Decimal("20")).to_integral_value())))

def _task_minutes_per_unit(s: Session, code: str, fallback: int) -> int:
    t = s.execute(select(LaborTask).where(LaborTask.code == code)).scalar_one_or_none()
    return int(t.minutes_per_unit) if t else int(fallback)

def generate_variant_extras(
    s: Session,
    inputs: ProjectInputs,
    variant_key: str,
) -> list[ExtraSpec]:
    """Generate additional positions based on ParamRule table.

    - Rules are evaluated with safe expressions (no arbitrary code).
    - Vars: area_m2, rooms, floors, apartments
    - Scoping: variant_key matches exact or 'any'; building_type matches exact or 'any'
    """
    v = (variant_key or "standard").lower().strip()
    btype = (inputs.building_type or "efh").lower().strip()
    area = _d(inputs.area_m2, Decimal("0"))
    rooms = _rooms_guess(area, inputs.rooms_total)
    floors = int(inputs.floors or 1)
    apartments = int(inputs.apartments or 0)
    if btype == "mfh" and apartments <= 0:
        apartments = 1

    rules = list(s.execute(
        select(ParamRule).where(ParamRule.enabled == True).order_by(ParamRule.priority, ParamRule.id)
    ).scalars().all())
    if not rules:
        return []

    vars = {"area_m2": float(area), "rooms": int(rooms), "floors": floors, "apartments": apartments}
    specs: list[ExtraSpec] = []
    for r in rules:
        rv = (r.variant_key or "any").lower()
        rb = (r.building_type or "any").lower()
        if rv not in ("any", v):
            continue
        if rb not in ("any", btype):
            continue

        qty = safe_eval(r.qty_expr, vars)
        if qty <= 0:
            continue

        key = (r.rate_key or "").strip()
        muc, task = _rate(s, key)
        line = lookup_line(s, key)
        item_id = int(line.item_id) if line and line.item_id else None

        desc = (r.description_tpl or "{rate_key}").replace("{rate_key}", key).replace("{variant}", v).replace("{building}", btype)

        specs.append(ExtraSpec(
            description=desc,
            qty=qty,
            unit=r.unit or "pcs",
            material_unit_cent=muc,
            labor_task_code=task or "STD-NYM",
            rate_key=key,
            item_id=item_id,
            note=r.note,
        ))

    return specs

def _rate(s: Session, key: str) -> tuple[int, str]:
    """Return (material_unit_cent, labor_task_code) from RateCard if present, else fallback constants."""
    line = lookup_line(s, key)
    if line:
        task = line.labor_task_code or "STD-NYM"
        return (int(line.material_unit_cent), task)
    # fallback
    if key in MATERIAL_RATES_CENT:
        return (int(MATERIAL_RATES_CENT[key]), "STD-NYM")
    return (0, "STD-NYM")
