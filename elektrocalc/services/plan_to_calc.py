from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from elektrocalc.db.models import PlanQtyMapping, CalcExtraLine
from elektrocalc.services.plans import compute_plan_quantities
from elektrocalc.services.ratecard_engine import compute_price_from_rate_key

def apply_plan_quantities_to_estimate(
    s: Session,
    project_id: int,
    plan_id: int,
    estimate_id: int,
    variant: str,
    labor_rate_per_min_cent: int,
    overhead_pct: str,
    profit_pct: str,
) -> list[CalcExtraLine]:
    q = compute_plan_quantities(s, plan_id)
    routes_m = q.get("routes_by_type_m", {}) or {}
    points = q.get("points_by_type", {}) or {}

    mappings = list(
        s.execute(select(PlanQtyMapping).where(PlanQtyMapping.project_id == project_id))
        .scalars()
        .all()
    )

    # variant override wins
    def find_mapping(kind: str, key: str) -> PlanQtyMapping | None:
        v = (variant or "").lower().strip()
        for m in mappings:
            if m.kind != kind or m.key != key:
                continue
            if (m.variant_key or "").lower().strip() == v:
                return m
        for m in mappings:
            if m.kind == kind and m.key == key and not m.variant_key:
                return m
        return None

    created: list[CalcExtraLine] = []

    def _factor(x: str) -> float:
        try:
            return float(str(x).replace(",", "."))
        except Exception:
            return 1.0

    # routes
    for rt, length_m in routes_m.items():
        m = find_mapping("route", rt)
        if not m:
            continue
        qty = float(length_m) * _factor(m.qty_factor)
        if qty <= 0:
            continue
        price = compute_price_from_rate_key(
            s,
            rate_key=m.rate_key,
            qty=qty,
            labor_rate_per_min_cent=labor_rate_per_min_cent,
            overhead_pct=overhead_pct,
            profit_pct=profit_pct,
        )
        x = CalcExtraLine(
            estimate_id=estimate_id,
            description=m.description or f"Route {rt}",
            rate_key=m.rate_key,
            qty=str(round(qty, 3)),
            unit=m.unit,
            material_total_cent=price["material_total_cent"],
            labor_total_cent=price["labor_total_cent"],
            labor_minutes=price["labor_minutes"],
            total_cent=price["total_cent"],
        )
        s.add(x)
        created.append(x)

    # points
    for pt, count in points.items():
        m = find_mapping("point", pt)
        if not m:
            continue
        qty = float(count) * _factor(m.qty_factor)
        if qty <= 0:
            continue
        price = compute_price_from_rate_key(
            s,
            rate_key=m.rate_key,
            qty=qty,
            labor_rate_per_min_cent=labor_rate_per_min_cent,
            overhead_pct=overhead_pct,
            profit_pct=profit_pct,
        )
        x = CalcExtraLine(
            estimate_id=estimate_id,
            description=m.description or f"Punkt {pt}",
            rate_key=m.rate_key,
            qty=str(round(qty, 3)),
            unit=m.unit,
            material_total_cent=price["material_total_cent"],
            labor_total_cent=price["labor_total_cent"],
            labor_minutes=price["labor_minutes"],
            total_cent=price["total_cent"],
        )
        s.add(x)
        created.append(x)

    s.commit()
    for x in created:
        s.refresh(x)
    return created
