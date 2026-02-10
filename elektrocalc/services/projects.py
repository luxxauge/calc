from __future__ import annotations
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from elektrocalc.db.models import Project, ProjectInputs
from elektrocalc.db.enums import InstallType, RenovationDepth

def list_projects(s: Session) -> list[Project]:
    return list(s.execute(select(Project).order_by(Project.updated_at.desc())).scalars().all())

def create_project(s: Session, name: str, customer_name: str | None, profile: str) -> Project:
    p = Project(name=name, customer_name=customer_name, profile=profile, updated_at=datetime.utcnow())
    s.add(p)
    s.flush()
    s.add(ProjectInputs(
        project_id=p.id,
        area_m2="0",
        floors=1,
        room_height_m="2.45",
        building_type="efh",
        apartments=None,
        install_type=InstallType.UP.value,
        renovation_depth=RenovationDepth.MEDIUM.value,
        distribution_factor="1.0",
        layout_factor="1.0",
        labor_rate_eur_h="72",
        overhead_pct="0",
        profit_pct="0",
    ))
    s.commit()
    s.refresh(p)
    return p

def get_project(s: Session, project_id: int) -> Project:
    return s.execute(select(Project).where(Project.id == project_id)).scalar_one()

def update_project_inputs(s: Session, project_id: int, data: dict) -> None:
    p = get_project(s, project_id)
    p.updated_at = datetime.utcnow()
    inp = p.inputs
    for k, v in data.items():
        if hasattr(inp, k):
            setattr(inp, k, v)
    s.commit()
