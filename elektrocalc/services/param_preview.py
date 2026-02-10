from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from elektrocalc.db.models import ParamRule, LaborTask
from elektrocalc.services.safe_eval import safe_eval
from elektrocalc.services.rate_card import lookup_line
from elektrocalc.services.calc_engine import _latest_vk_cent  # reuse
from elektrocalc.services.calc_engine import _qty_to_decimal  # reuse

def preview_param_extras(
    s: Session,
    *,
    variant: str,
    building_type: str,
    area_m2: float,
    rooms: int,
    floors: int,
    apartments: int,
    labor_rate_per_min_cent: int,
    overhead_pct: str = "0",
    profit_pct: str = "0",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    v = (variant or "standard").lower().strip()
    b = (building_type or "efh").lower().strip()
    vars = {"area_m2": float(area_m2 or 0), "rooms": int(rooms or 0), "floors": int(floors or 1), "apartments": int(apartments or 0)}
    rules = list(s.execute(select(ParamRule).where(ParamRule.enabled==True).order_by(ParamRule.priority, ParamRule.id)).scalars().all())

    extras: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    for r in rules:
        rv = (r.variant_key or "any").lower()
        rb = (r.building_type or "any").lower()
        if rv not in ("any", v):
            continue
        if rb not in ("any", b):
            continue

        status = "ok"
        hint = ""
        qty = Decimal("0")
        try:
            qty = safe_eval(r.qty_expr, vars)
            if qty <= 0:
                status = "skip"
                hint = "qty <= 0"
        except Exception as e:
            status = "error"
            hint = str(e)

        # rate-key check
        line = lookup_line(s, r.rate_key)
        if line is None:
            status = "error"
            hint = (hint + " | " if hint else "") + "rate_key not found in ratecard"

        checks.append({
            "id": r.id, "priority": r.priority, "variant_key": r.variant_key, "building_type": r.building_type,
            "rate_key": r.rate_key, "qty_expr": r.qty_expr, "qty": str(qty), "status": status, "note": hint,
        })

        if status != "ok":
            continue

        qty_ex = _qty_to_decimal(str(qty))
        # material unit
        unit_cent = int(line.material_unit_cent)
        item_id = int(line.item_id) if line.item_id else None
        if item_id:
            try:
                unit_cent = _latest_vk_cent(s, item_id)
            except Exception:
                pass
        material_cent = int((Decimal(unit_cent) * qty_ex).to_integral_value())

        # labor via task
        task_code = line.labor_task_code or "STD-NYM"
        task = s.execute(select(LaborTask).where(LaborTask.code==task_code)).scalar_one_or_none()
        mpu = int(task.minutes_per_unit) if task else 10
        labor_minutes = int((Decimal(mpu) * qty_ex).to_integral_value())
        labor_cent = int((Decimal(labor_minutes) * Decimal(labor_rate_per_min_cent)).to_integral_value())

        # overhead/profit
        from decimal import Decimal as D
        oh = D(str(overhead_pct).replace(",", ".") or "0")
        pr = D(str(profit_pct).replace(",", ".") or "0")
        total = D(material_cent + labor_cent) * (D("1") + oh + pr)
        total_cent = int(total.to_integral_value())

        desc = (r.description_tpl or "{rate_key}").replace("{rate_key}", r.rate_key).replace("{variant}", v).replace("{building}", b)
        extras.append({
            "description": desc,
            "rate_key": r.rate_key,
            "qty": str(qty_ex),
            "unit": r.unit or line.unit or "pcs",
            "unit_cent": unit_cent,
            "item_id": item_id,
            "material_cent": material_cent,
            "labor_task_code": task_code,
            "labor_minutes": labor_minutes,
            "labor_cent": labor_cent,
            "total_cent": total_cent,
            "note": r.note,
        })

    return extras, checks
