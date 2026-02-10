from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from elektrocalc.db.models import (
    LvDocument, LvPosition, ItemPrice, CalcEstimate, CalcEstimateLine,
    LaborRule, LaborTask, VariantProfile, VariantRule, CalcExtraLine, ProjectInputs
)



from sqlalchemy import asc
from decimal import Decimal

def _match_variant_rule(s: Session, p: LvPosition, task_code: str | None, profile_id: int) -> VariantRule | None:
    text = ((p.short_text or "") + " " + (p.long_text or "")).lower()
    rules = list(s.execute(
        select(VariantRule).where(
            VariantRule.variant_profile_id == profile_id,
            VariantRule.enabled == True
        ).order_by(asc(VariantRule.priority), asc(VariantRule.id))
    ).scalars().all())
    for r in rules:
        if r.match_task_code and task_code and r.match_task_code.strip().lower() == task_code.strip().lower():
            return r
        if r.match_pattern:
            if r.is_regex:
                try:
                    if re.search(r.match_pattern, text, flags=re.IGNORECASE):
                        return r
                except re.error:
                    continue
            else:
                if r.match_pattern.lower() in text:
                    return r
    return None

def _apply_variant_rules(
    s: Session,
    p: LvPosition,
    base_material_cent: int,
    base_labor_minutes: int,
    labor_task_code: str | None,
    variant_key: str,
) -> tuple[int, int, str | None]:
    prof = s.execute(select(VariantProfile).where(VariantProfile.key == variant_key)).scalar_one_or_none()
    if prof is None:
        return (base_material_cent, base_labor_minutes, None)
    r = _match_variant_rule(s, p, labor_task_code, prof.id)
    if r is None:
        return (base_material_cent, base_labor_minutes, None)

    try:
        lm = Decimal(str(r.labor_multiplier).replace(",", "."))
    except Exception:
        lm = Decimal("1.00")
    try:
        mm = Decimal(str(r.material_multiplier).replace(",", "."))
    except Exception:
        mm = Decimal("1.00")

    mat = int((Decimal(base_material_cent) * mm).to_integral_value())
    mins = int((Decimal(base_labor_minutes) * lm).to_integral_value()) + int(r.add_labor_minutes or 0)
    info = f"variant:{variant_key} rule#{r.id}"
    return (mat, max(0, mins), info)

VARIANT_FACTOR = {
    "standard": Decimal("1.00"),
    "komfort": Decimal("1.15"),
    "premium": Decimal("1.30"),
}

def _d(v: Any, default: Decimal = Decimal("0")) -> Decimal:
    if v is None:
        return default
    s = str(v).strip().replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return default

def _qty_to_decimal(qty_str: str) -> Decimal:
    q = _d(qty_str, Decimal("1"))
    return q if q > 0 else Decimal("1")



import re
from sqlalchemy import asc

def _match_labor_task(s: Session, p: LvPosition) -> tuple[LaborTask | None, str | None]:
    """Return (task, reason) if a rule matches, else (None,None)."""
    text = ((p.short_text or "") + " " + (p.long_text or "")).lower()
    rules = list(s.execute(
        select(LaborRule).where(LaborRule.enabled == True).order_by(asc(LaborRule.priority), asc(LaborRule.id))
    ).scalars().all())
    for r in rules:
        if r.is_regex:
            try:
                if re.search(r.pattern, text, flags=re.IGNORECASE):
                    return (r.task, f"regex:{r.pattern}")
            except re.error:
                continue
        else:
            if r.pattern.lower() in text:
                return (r.task, f"substr:{r.pattern}")
    return (None, None)

def _labor_minutes_rule_based(s: Session, p: LvPosition, qty: Decimal) -> tuple[int, str, str] | None:
    task, reason = _match_labor_task(s, p)
    if task is None:
        return None
    # unit mismatch: if LV unit differs from task.unit, still use LV qty but warn later (v1.4: accept)
    minutes = int((Decimal(task.minutes_per_unit) * qty).to_integral_value())
    minutes = max(0, minutes)
    return (minutes, task.code, reason or "")

def _labor_minutes_for_position(p: LvPosition, qty: Decimal, s: Session | None = None) -> tuple[int, str, str | None, str | None]:
    # Prefer rule-based catalog if session provided.
    if s is not None:
        rb = _labor_minutes_rule_based(s, p, qty)
        if rb is not None:
            minutes, task_code, rule_info = rb
            return (minutes, "rule", task_code, rule_info)

    # Heuristic fallback (v1.3).
    unit = (p.unit or "pcs").lower()
    text = (p.short_text or "").lower()

    if unit in ("h", "std"):
        minutes = int((qty * 60).to_integral_value())
        return (max(0, minutes), "heuristic", None, None)

    if unit in ("m", "lfm"):
        base = Decimal("2.0")  # 2 min per meter
        minutes = int((qty * base).to_integral_value())
    elif unit in ("m²", "m2", "qm"):
        base = Decimal("3.0")
        minutes = int((qty * base).to_integral_value())
    else:
        base = Decimal("10.0")  # 10 min per piece
        minutes = int((qty * base).to_integral_value())

    # Keyword boosts
    boosts = [
        ("schalter", 3),
        ("steckdose", 4),
        ("leuchte", 5),
        ("verteiler", 30),
        ("uv", 30),
        ("kabel", 1),
        ("leitung", 1),
        ("daten", 4),
        ("netzwerk", 6),
    ]
    for kw, add in boosts:
        if kw in text:
            minutes += add
    return (max(0, minutes), "heuristic", None, None)

def _latest_vk_cent(s: Session, item_id: int) -> int:
    # Prefer latest VK (if any). If none, 0.
    ip = s.execute(
        select(ItemPrice).where(ItemPrice.item_id == item_id).order_by(desc(ItemPrice.created_at))
    ).scalar_one_or_none()
    return int(ip.price_vk_cent) if ip else 0

def run_estimate(
    s: Session,
    lv_document_id: int,
    variant: str,
    labor_rate_cent: int = 6500,
    overhead_pct: str = "0.15",
    profit_pct: str = "0.10",
) -> CalcEstimate:
    v = (variant or "").lower().strip()
    if v not in VARIANT_FACTOR:
        raise ValueError("variant must be standard|komfort|premium")

    # VariantProfile defaults (optional)
    prof = s.execute(select(VariantProfile).where(VariantProfile.key == v)).scalar_one_or_none()
    if (overhead_pct is None or str(overhead_pct).strip() == "") and prof is not None:
        overhead_pct = prof.default_overhead_pct
    if (profit_pct is None or str(profit_pct).strip() == "") and prof is not None:
        profit_pct = prof.default_profit_pct

        raise ValueError("variant must be standard|komfort|premium")

    doc = s.execute(select(LvDocument).where(LvDocument.id == lv_document_id)).scalar_one()

    est = CalcEstimate(
        lv_document_id=doc.id,
        variant=v,
        labor_rate_cent=int(labor_rate_cent),
        overhead_pct=str(overhead_pct),
        profit_pct=str(profit_pct),
        created_at=datetime.utcnow(),
    )
    s.add(est)
    s.flush()

    factor = VARIANT_FACTOR[v]
    labor_rate_per_min_cent = Decimal(labor_rate_cent) / Decimal("60")

    positions = list(s.execute(select(LvPosition).where(LvPosition.lv_document_id == doc.id)).scalars().all())
    for p in positions:
        qty = _qty_to_decimal(p.qty)
        unit = p.unit or "pcs"

        material_cent = 0
        if p.match and p.match.item_id:
            vk_unit_cent = _latest_vk_cent(s, p.match.item_id)
            # assume price is per unit of LV qty
            material_cent = int((Decimal(vk_unit_cent) * qty).to_integral_value())

        labor_minutes, labor_source, labor_task_code, labor_rule_info = _labor_minutes_for_position(p, qty, s)
        # base variant factor (coarse)
        labor_minutes = int((Decimal(labor_minutes) * factor).to_integral_value())
        # apply fine-grained DIN variant rules (optional)
        material_cent, labor_minutes, vinfo = _apply_variant_rules(s, p, material_cent, labor_minutes, labor_task_code, v)
        if vinfo:
            labor_rule_info = (labor_rule_info + " | " + vinfo) if labor_rule_info else vinfo

        labor_cent = int((Decimal(labor_minutes) * labor_rate_per_min_cent).to_integral_value())
        base_total = Decimal(material_cent + labor_cent)

        oh = _d(overhead_pct, Decimal("0"))
        pr = _d(profit_pct, Decimal("0"))
        total = base_total * (Decimal("1") + oh + pr)
        total_cent = int(total.to_integral_value())

        s.add(CalcEstimateLine(
            estimate_id=est.id,
            lv_position_id=p.id,
            qty=str(qty),
            unit=unit,
            material_cent=int(material_cent),
            labor_minutes=int(labor_minutes),
            labor_cent=int(labor_cent),
            total_cent=int(total_cent),
            labor_source=labor_source,
            labor_task_code=labor_task_code,
            labor_rule_info=labor_rule_info,
        ))

    s.commit()
    s.refresh(est)
    return est

def list_estimates(s: Session, lv_document_id: int) -> list[CalcEstimate]:
    return list(s.execute(
        select(CalcEstimate).where(CalcEstimate.lv_document_id == lv_document_id).order_by(desc(CalcEstimate.id))
    ).scalars().all())

def get_estimate(s: Session, estimate_id: int) -> CalcEstimate:
    return s.execute(select(CalcEstimate).where(CalcEstimate.id == estimate_id)).scalar_one()

def list_estimate_lines(s: Session, estimate_id: int) -> list[CalcEstimateLine]:
    return list(s.execute(select(CalcEstimateLine).where(CalcEstimateLine.estimate_id==estimate_id)).scalars().all())

def summarize_estimate(lines: list[CalcEstimateLine], extra_lines: list[CalcExtraLine] | None = None) -> dict[str,int]:
    extra_lines = extra_lines or []
    mat = sum(int(l.material_cent) for l in lines) + sum(int(l.material_cent) for l in extra_lines)
    lab = sum(int(l.labor_cent) for l in lines) + sum(int(l.labor_cent) for l in extra_lines)
    tot = sum(int(l.total_cent) for l in lines) + sum(int(l.total_cent) for l in extra_lines)
    mins = sum(int(l.labor_minutes) for l in lines) + sum(int(l.labor_minutes) for l in extra_lines)
    return {"material_cent": mat, "labor_cent": lab, "total_cent": tot, "labor_minutes": mins}
