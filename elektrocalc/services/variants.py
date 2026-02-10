from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy import select, asc
from sqlalchemy.orm import Session

from elektrocalc.db.models import VariantProfile, VariantRule

def list_profiles(s: Session) -> list[VariantProfile]:
    return list(s.execute(select(VariantProfile).order_by(asc(VariantProfile.id))).scalars().all())

def get_profile_by_key(s: Session, key: str) -> VariantProfile | None:
    return s.execute(select(VariantProfile).where(VariantProfile.key == key)).scalar_one_or_none()

def list_rules_for_profile(s: Session, profile_id: int) -> list[VariantRule]:
    return list(s.execute(
        select(VariantRule).where(VariantRule.variant_profile_id == profile_id).order_by(asc(VariantRule.priority), asc(VariantRule.id))
    ).scalars().all())

def create_rule(
    s: Session,
    profile_id: int,
    match_task_code: str | None,
    match_pattern: str | None,
    is_regex: bool,
    priority: int,
    labor_multiplier: str,
    material_multiplier: str,
    add_labor_minutes: int,
    note: str | None,
    enabled: bool = True,
) -> VariantRule:
    if not match_task_code and not match_pattern:
        raise ValueError("match_task_code or match_pattern required")
    if is_regex and match_pattern:
        try:
            re.compile(match_pattern)
        except re.error as e:
            raise ValueError(f"invalid regex: {e}")

    def _dec(sv: str) -> str:
        try:
            d = Decimal(str(sv).replace(",", "."))
            if d <= 0:
                raise ValueError
            return str(d.quantize(Decimal("0.01")))
        except Exception:
            raise ValueError("invalid multiplier")

    r = VariantRule(
        variant_profile_id=profile_id,
        match_task_code=(match_task_code or "").strip() or None,
        match_pattern=(match_pattern or "").strip() or None,
        is_regex=bool(is_regex),
        priority=int(priority),
        enabled=bool(enabled),
        labor_multiplier=_dec(labor_multiplier),
        material_multiplier=_dec(material_multiplier),
        add_labor_minutes=int(add_labor_minutes),
        note=(note or "").strip() or None,
    )
    s.add(r)
    s.commit()
    s.refresh(r)
    return r

def delete_rule(s: Session, rule_id: int) -> None:
    r = s.get(VariantRule, rule_id)
    if r:
        s.delete(r)
        s.commit()

def seed_defaults_if_empty(s: Session) -> None:
    if s.execute(select(VariantProfile).limit(1)).scalar_one_or_none() is not None:
        return

    std = VariantProfile(key="standard", name="Standard (DIN 18015)", default_overhead_pct="0.15", default_profit_pct="0.10", created_at=datetime.utcnow())
    kom = VariantProfile(key="komfort", name="Komfort (DIN 18015)", default_overhead_pct="0.15", default_profit_pct="0.10", created_at=datetime.utcnow())
    pre = VariantProfile(key="premium", name="Premium (DIN 18015)", default_overhead_pct="0.15", default_profit_pct="0.10", created_at=datetime.utcnow())
    s.add_all([std, kom, pre])
    s.flush()

    # Minimal starter rules (v1): Komfort/Premium etwas mehr Aufwand/Material auf Endgeräte
    # Match via task codes from default time catalog (STD-STECK/STD-SCHALT/STD-LEUCHT)
    s.add_all([
        VariantRule(variant_profile_id=kom.id, match_task_code="STD-STECK", match_pattern=None, is_regex=False, priority=10, enabled=True,
                    labor_multiplier="1.10", material_multiplier="1.05", add_labor_minutes=0, note="Komfort: Steckdosen etwas höherer Aufwand/Qualität"),
        VariantRule(variant_profile_id=kom.id, match_task_code="STD-SCHALT", match_pattern=None, is_regex=False, priority=20, enabled=True,
                    labor_multiplier="1.08", material_multiplier="1.05", add_labor_minutes=0, note="Komfort: Schalterprogramm höherwertig"),
        VariantRule(variant_profile_id=pre.id, match_task_code="STD-STECK", match_pattern=None, is_regex=False, priority=10, enabled=True,
                    labor_multiplier="1.20", material_multiplier="1.10", add_labor_minutes=1, note="Premium: Steckdosen (Mehrgeräte/Design)"),
        VariantRule(variant_profile_id=pre.id, match_task_code="STD-SCHALT", match_pattern=None, is_regex=False, priority=20, enabled=True,
                    labor_multiplier="1.15", material_multiplier="1.10", add_labor_minutes=1, note="Premium: Schalterprogramm Design"),
        VariantRule(variant_profile_id=pre.id, match_task_code="STD-LEUCHT", match_pattern=None, is_regex=False, priority=30, enabled=True,
                    labor_multiplier="1.15", material_multiplier="1.00", add_labor_minutes=2, note="Premium: Leuchten/Anschlussaufwand"),
    ])
    s.commit()
