from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from elektrocalc.db.models import PlanQtyMapping

DEFAULTS = [
    # routes
    dict(kind="route", key="CABLE_ROUTE", rate_key="ROUTE_CABLE", unit="m", qty_factor="1.25", description="Leitungsweg Kabel (m) inkl. Verteiler-/Weg-Faktor"),
    dict(kind="route", key="TRUNKING", rate_key="ROUTE_TRUNKING", unit="m", qty_factor="1.10", description="Kabelkanal (m) inkl. Zuschlag"),
    dict(kind="route", key="CONDUIT", rate_key="ROUTE_CONDUIT", unit="m", qty_factor="1.15", description="Leerrohr (m) inkl. Zuschlag"),
    # points
    dict(kind="point", key="SOCKET", rate_key="PT_SOCKET", unit="St", qty_factor="1", description="Steckdose"),
    dict(kind="point", key="DATA", rate_key="PT_DATA", unit="St", qty_factor="1", description="Datendose"),
    dict(kind="point", key="LIGHT", rate_key="PT_LIGHT", unit="St", qty_factor="1", description="Leuchtenauslass"),
]

def seed_defaults_if_empty(s: Session, project_id: int) -> None:
    exists = s.execute(select(PlanQtyMapping).where(PlanQtyMapping.project_id == project_id)).first()
    if exists:
        return
    for d in DEFAULTS:
        s.add(PlanQtyMapping(project_id=project_id, **d))
    s.commit()

def list_mappings(s: Session, project_id: int) -> list[PlanQtyMapping]:
    return list(
        s.execute(
            select(PlanQtyMapping)
            .where(PlanQtyMapping.project_id == project_id)
            .order_by(PlanQtyMapping.kind, PlanQtyMapping.key, PlanQtyMapping.variant_key)
        )
        .scalars()
        .all()
    )

def upsert_mapping(
    s: Session,
    project_id: int,
    kind: str,
    key: str,
    variant_key: str | None,
    rate_key: str,
    unit: str,
    qty_factor: str,
    description: str | None,
) -> PlanQtyMapping:
    q = select(PlanQtyMapping).where(
        PlanQtyMapping.project_id == project_id,
        PlanQtyMapping.kind == kind,
        PlanQtyMapping.key == key,
        PlanQtyMapping.variant_key == variant_key,
    )
    m = s.execute(q).scalar_one_or_none()
    if m is None:
        m = PlanQtyMapping(
            project_id=project_id,
            kind=kind,
            key=key,
            variant_key=variant_key,
            rate_key=rate_key,
            unit=unit,
            qty_factor=qty_factor,
            description=description,
        )
        s.add(m)
    else:
        m.rate_key = rate_key
        m.unit = unit
        m.qty_factor = qty_factor
        m.description = description
    s.commit()
    s.refresh(m)
    return m

def delete_mapping(s: Session, mapping_id: int) -> None:
    m = s.execute(select(PlanQtyMapping).where(PlanQtyMapping.id == mapping_id)).scalar_one()
    s.delete(m)
    s.commit()
