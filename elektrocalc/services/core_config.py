from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from elektrocalc.db.models import CoreConfigVersion

def get_or_create_initial_config_version(s: Session) -> CoreConfigVersion:
    v = s.execute(select(CoreConfigVersion).order_by(CoreConfigVersion.id.desc()).limit(1)).scalar_one_or_none()
    if v:
        return v
    v = CoreConfigVersion(notes="Initial core config (auto)")
    s.add(v)
    s.commit()
    s.refresh(v)
    return v

def latest_config_version(s: Session) -> CoreConfigVersion:
    return s.execute(select(CoreConfigVersion).order_by(CoreConfigVersion.id.desc()).limit(1)).scalar_one()
