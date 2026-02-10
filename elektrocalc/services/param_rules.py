from __future__ import annotations

from datetime import datetime
from sqlalchemy import select, asc
from sqlalchemy.orm import Session

from elektrocalc.db.models import ParamRule

def seed_defaults_if_empty(s: Session) -> None:
    if s.execute(select(ParamRule).limit(1)).scalar_one_or_none() is not None:
        return
    s.add_all([
        ParamRule(variant_key="komfort", building_type="any", enabled=True, priority=10, rate_key="socket_kom",
                  description_tpl="Zusatz Steckdosen (komfort)", unit="pcs", qty_expr="max(0, (6-4)*rooms)", note="Baseline Standard=4 Steckdosen/Raum", created_at=datetime.utcnow()),
        ParamRule(variant_key="premium", building_type="any", enabled=True, priority=10, rate_key="socket_pre",
                  description_tpl="Zusatz Steckdosen (premium)", unit="pcs", qty_expr="max(0, (8-4)*rooms)", note="Baseline Standard=4 Steckdosen/Raum", created_at=datetime.utcnow()),
        ParamRule(variant_key="komfort", building_type="any", enabled=True, priority=20, rate_key="data_kom",
                  description_tpl="Zusatz Datendosen / Netzwerkpunkte (komfort)", unit="pcs", qty_expr="1*rooms", note="1/Raum", created_at=datetime.utcnow()),
        ParamRule(variant_key="premium", building_type="any", enabled=True, priority=20, rate_key="data_pre",
                  description_tpl="Zusatz Datendosen / Netzwerkpunkte (premium)", unit="pcs", qty_expr="2*rooms", note="2/Raum", created_at=datetime.utcnow()),
    ])
    s.commit()

def list_rules(s: Session) -> list[ParamRule]:
    return list(s.execute(select(ParamRule).order_by(asc(ParamRule.priority), asc(ParamRule.id))).scalars().all())

def create_rule(s: Session, **kwargs) -> ParamRule:
    r = ParamRule(**kwargs, created_at=datetime.utcnow())
    s.add(r)
    s.commit()
    s.refresh(r)
    return r

def delete_rule(s: Session, rule_id: int) -> None:
    r = s.get(ParamRule, rule_id)
    if r:
        s.delete(r)
        s.commit()
