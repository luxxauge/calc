from __future__ import annotations
from datetime import datetime
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import select

from elektrocalc.db.models import CalcRun, CalcRunQuantity, Project, Plan, PlanPoint
from elektrocalc.db.enums import QuantitySource
from elektrocalc.services.core_config import latest_config_version
from elektrocalc.util.hashing import stable_json_hash

def _hash_inputs(project: Project) -> str:
    inp = project.inputs
    data = {c.name: getattr(inp, c.name) for c in inp.__table__.columns if c.name not in ("id","project_id")}
    return stable_json_hash(data)

def _hash_plan(plan: Plan | None) -> str | None:
    if not plan:
        return None
    return stable_json_hash({
        "plan_id": plan.id,
        "scale": plan.scale_m_per_px,
        "rooms": len(plan.rooms),
        "points": len(plan.points),
        "routes": len(plan.routes),
    })

def recalc_variant(s: Session, project_id: int, variant_key: str) -> CalcRun:
    project = s.execute(select(Project).where(Project.id == project_id)).scalar_one()
    cfg = latest_config_version(s)
    inputs_hash = _hash_inputs(project)

    # choose latest plan (if any)
    plan = project.plans[-1] if project.plans else None
    plan_hash = _hash_plan(plan)

    run = CalcRun(
        project_id=project_id,
        variant_key=variant_key,
        created_at=datetime.utcnow(),
        core_config_version_id=cfg.id,
        inputs_hash=inputs_hash,
        plan_hash=plan_hash,
        total_material_ek_cent=0,
        total_labor_sec=0,
        total_net_cent=0,
        total_vat_cent=0,
        total_gross_cent=0,
        calc_params={"mode": "minimal", "note": "quantities from plan points only (v1)"},
    )
    s.add(run)
    s.flush()

    if plan:
        counts = Counter([pt.point_type for pt in plan.points])
        for item_code, cnt in counts.items():
            s.add(CalcRunQuantity(
                calc_run_id=run.id,
                room_ref=None,
                item_code=item_code,
                qty=str(int(cnt)),
                unit="pcs",
                source=QuantitySource.PLAN_POINTS.value,
            ))

    s.commit()
    s.refresh(run)
    return run

def list_calc_runs(s: Session, project_id: int, variant_key: str) -> list[CalcRun]:
    return list(s.execute(
        select(CalcRun).where(CalcRun.project_id == project_id, CalcRun.variant_key == variant_key).order_by(CalcRun.id.desc())
    ).scalars().all())
