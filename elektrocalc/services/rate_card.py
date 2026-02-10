from __future__ import annotations

from datetime import datetime
from sqlalchemy import select, asc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from elektrocalc.db.models import RateCard, RateCardLine

DEFAULT_CARD_NAME = "Default"

DEFAULT_LINES = [
    # key, description, unit, material_unit_cent, labor_task_code
    ("socket_std", "Steckdose Standard (Zusatz)", "pcs", 900, "STD-STECK"),
    ("socket_kom", "Steckdose Komfort (Zusatz)", "pcs", 1400, "STD-STECK"),
    ("socket_pre", "Steckdose Premium (Zusatz)", "pcs", 2200, "STD-STECK"),
    ("data_std", "Datendose Standard (Zusatz)", "pcs", 1800, "STD-NYM"),
    ("data_kom", "Datendose Komfort (Zusatz)", "pcs", 2400, "STD-NYM"),
    ("data_pre", "Datendose Premium (Zusatz)", "pcs", 3200, "STD-NYM"),
]

def seed_defaults_if_empty(s: Session) -> None:
    if s.execute(select(RateCard).limit(1)).scalar_one_or_none() is not None:
        return
    card = RateCard(name=DEFAULT_CARD_NAME, currency="EUR", created_at=datetime.utcnow())
    s.add(card)
    s.flush()
    for key, desc, unit, muc, task in DEFAULT_LINES:
        s.add(RateCardLine(
            rate_card_id=card.id,
            key=key,
            description=desc,
            unit=unit,
            material_unit_cent=int(muc),
            labor_task_code=task,
            item_id=None,
            created_at=datetime.utcnow()
        ))
    s.commit()

def list_cards(s: Session) -> list[RateCard]:
    return list(s.execute(select(RateCard).order_by(asc(RateCard.id))).scalars().all())

def get_card(s: Session, card_id: int) -> RateCard:
    return s.execute(select(RateCard).where(RateCard.id == card_id)).scalar_one()

def get_default_card(s: Session) -> RateCard:
    c = s.execute(select(RateCard).where(RateCard.name == DEFAULT_CARD_NAME)).scalar_one_or_none()
    if c is None:
        seed_defaults_if_empty(s)
        c = s.execute(select(RateCard).where(RateCard.name == DEFAULT_CARD_NAME)).scalar_one()
    return c

def list_lines(s: Session, card_id: int) -> list[RateCardLine]:
    return list(s.execute(select(RateCardLine).where(RateCardLine.rate_card_id==card_id).order_by(asc(RateCardLine.key))).scalars().all())

def upsert_line(
    s: Session,
    card_id: int,
    key: str,
    description: str,
    unit: str,
    material_unit_cent: int,
    labor_task_code: str | None,
    item_id: int | None,
) -> RateCardLine:
    key = (key or "").strip()
    if not key:
        raise ValueError("key required")
    line = s.execute(select(RateCardLine).where(RateCardLine.rate_card_id==card_id, RateCardLine.key==key)).scalar_one_or_none()
    if line is None:
        line = RateCardLine(rate_card_id=card_id, key=key, description=description.strip() or key, unit=unit, material_unit_cent=int(material_unit_cent), labor_task_code=(labor_task_code or "").strip() or None, item_id=item_id, created_at=datetime.utcnow())
        s.add(line)
    else:
        line.description = description.strip() or line.description
        line.unit = unit
        line.material_unit_cent = int(material_unit_cent)
        line.labor_task_code = (labor_task_code or "").strip() or None
        line.item_id = item_id
    s.commit()
    s.refresh(line)
    return line

def delete_line(s: Session, line_id: int) -> None:
    line = s.get(RateCardLine, line_id)
    if line:
        s.delete(line)
        s.commit()

def lookup_line(s: Session, key: str, card_id: int | None = None) -> RateCardLine | None:
    if card_id is None:
        card = get_default_card(s)
        card_id = card.id
    return s.execute(select(RateCardLine).where(RateCardLine.rate_card_id==card_id, RateCardLine.key==key)).scalar_one_or_none()
