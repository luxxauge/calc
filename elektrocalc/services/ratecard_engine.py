from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from elektrocalc.db.models import RateCardLine
from elektrocalc.services.rate_card import get_default_card

def compute_price_from_rate_key(
    s: Session,
    rate_key: str,
    qty: float,
    labor_rate_per_min_cent: int,
    overhead_pct: str = "0",
    profit_pct: str = "0",
) -> dict:
    card = get_default_card(s)
    line = (
        s.execute(
            select(RateCardLine).where(
                RateCardLine.rate_card_id == card.id, RateCardLine.rate_key == rate_key
            )
        )
        .scalars()
        .first()
    )
    if line is None:
        return {"material_total_cent": 0, "labor_total_cent": 0, "labor_minutes": 0, "total_cent": 0}

    mat_cent = int(line.material_unit_cent or 0)
    labor_min = int(line.labor_min_per_unit or 0)

    material_total_cent = int(round(qty * mat_cent))
    labor_minutes = int(round(qty * labor_min))
    labor_total_cent = int(labor_minutes * int(labor_rate_per_min_cent))
    base = material_total_cent + labor_total_cent

    def _pct(x: str) -> float:
        try:
            return float(str(x).replace(",", "."))
        except Exception:
            return 0.0

    total = base
    oh = _pct(overhead_pct)
    pr = _pct(profit_pct)
    if oh:
        total = int(round(total * (1.0 + oh)))
    if pr:
        total = int(round(total * (1.0 + pr)))

    return {
        "material_total_cent": material_total_cent,
        "labor_total_cent": labor_total_cent,
        "labor_minutes": labor_minutes,
        "total_cent": total,
    }
