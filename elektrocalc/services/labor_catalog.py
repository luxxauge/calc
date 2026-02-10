from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, asc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from elektrocalc.db.models import LaborTask, LaborRule

VALID_UNITS = ["pcs", "m", "m²", "h"]

def list_tasks(s: Session) -> list[LaborTask]:
    return list(s.execute(select(LaborTask).order_by(asc(LaborTask.code))).scalars().all())

def list_rules(s: Session) -> list[LaborRule]:
    return list(s.execute(select(LaborRule).order_by(asc(LaborRule.priority), asc(LaborRule.id))).scalars().all())

def create_task(s: Session, code: str, name: str, unit: str, minutes_per_unit: int, notes: str | None = None) -> LaborTask:
    code = (code or "").strip()
    name = (name or "").strip()
    unit = (unit or "pcs").strip()
    if not code or not name:
        raise ValueError("code and name required")
    if unit not in VALID_UNITS:
        raise ValueError("invalid unit")
    if minutes_per_unit < 0 or minutes_per_unit > 24*60:
        raise ValueError("minutes_per_unit out of range")
    t = LaborTask(code=code, name=name, unit=unit, minutes_per_unit=int(minutes_per_unit), notes=notes, created_at=datetime.utcnow())
    s.add(t)
    try:
        s.commit()
    except IntegrityError:
        s.rollback()
        raise ValueError("code already exists")
    s.refresh(t)
    return t

def delete_task(s: Session, task_id: int) -> None:
    t = s.get(LaborTask, task_id)
    if t:
        s.delete(t)
        s.commit()

def create_rule(s: Session, pattern: str, is_regex: bool, priority: int, task_id: int, enabled: bool=True) -> LaborRule:
    pattern = (pattern or "").strip()
    if not pattern:
        raise ValueError("pattern required")
    if priority < 0 or priority > 100000:
        raise ValueError("priority out of range")
    if is_regex:
        # validate regex
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"invalid regex: {e}")
    r = LaborRule(pattern=pattern, is_regex=bool(is_regex), priority=int(priority), task_id=int(task_id), enabled=bool(enabled), created_at=datetime.utcnow())
    s.add(r)
    s.commit()
    s.refresh(r)
    return r

def delete_rule(s: Session, rule_id: int) -> None:
    r = s.get(LaborRule, rule_id)
    if r:
        s.delete(r)
        s.commit()

def seed_defaults_if_empty(s: Session) -> None:
    # minimal starter set; safe to call multiple times
    if s.execute(select(LaborTask).limit(1)).scalar_one_or_none() is not None:
        return
    create_task(s, "STD-STECK", "Steckdose setzen (UP/AP)", "pcs", 12, "Starterwert")
    create_task(s, "STD-SCHALT", "Schalter setzen (UP/AP)", "pcs", 10, "Starterwert")
    create_task(s, "STD-LEUCHT", "Leuchte anschließen", "pcs", 15, "Starterwert")
    create_task(s, "STD-NYM", "NYM Leitung verlegen", "m", 2, "Starterwert")
    # rules
    tasks = {t.code: t.id for t in list_tasks(s)}
    create_rule(s, "steckdose", False, 10, tasks["STD-STECK"], True)
    create_rule(s, "schalter", False, 20, tasks["STD-SCHALT"], True)
    create_rule(s, "leuchte", False, 30, tasks["STD-LEUCHT"], True)
    create_rule(s, "nym", False, 40, tasks["STD-NYM"], True)
