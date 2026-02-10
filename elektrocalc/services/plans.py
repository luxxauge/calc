from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Tuple

import fitz  # PyMuPDF
from PIL import Image

from sqlalchemy.orm import Session
from sqlalchemy import select

from elektrocalc.settings import ASSETS_ROOT
from elektrocalc.util.hashing import sha256_hex
from elektrocalc.util.files import atomic_copy, atomic_write_bytes, ensure_dir
from elektrocalc.db.models import PlanAsset, Plan, PlanRoom, PlanPoint, PlanRoute
from elektrocalc.db.enums import PlanFileType

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB safety limit

SUPPORTED = {".pdf": PlanFileType.PDF.value, ".jpg": PlanFileType.JPG.value, ".jpeg": PlanFileType.JPG.value, ".png": PlanFileType.PNG.value}

def _render_pdf_page_to_png(pdf_path: Path, page_index: int, dpi: int) -> bytes:
    """Render a single PDF page to PNG bytes (robust)."""
    try:
        doc = fitz.open(pdf_path.as_posix())
    except Exception as e:
        raise ValueError(f"Cannot open PDF: {pdf_path.name}") from e
    try:
        if doc.page_count <= 0:
            raise ValueError("PDF has no pages.")
        idx = max(0, min(int(page_index), doc.page_count - 1))
        page = doc.load_page(idx)
        zoom = float(dpi) / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix.tobytes("png")
    except Exception as e:
        raise ValueError(f"Failed to render PDF page {page_index} at {dpi} dpi.") from e
    finally:
        doc.close()

def _normalize_image_to_png(image_path: Path, max_width: int | None = None) -> bytes:
    """Load an image and return PNG bytes (optionally downscaled)."""
    import io
    with Image.open(image_path) as im:
        im = im.convert("RGB")
        if max_width and im.size[0] > max_width:
            ratio = max_width / im.size[0]
            new_size = (max(1, int(im.size[0] * ratio)), max(1, int(im.size[1] * ratio)))
            im = im.resize(new_size)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()

def create_plan_from_upload(
    s: Session,
    project_id: int,
    filename: str,
    tmp_path: Path,
    plan_name: str,
    pdf_page_index: int | None = None,
    preview_dpi: int = 120,
    work_dpi: int = 250,
) -> Plan:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {ext}")
    ftype = SUPPORTED[ext]

    if tmp_path.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload too large (> {MAX_UPLOAD_BYTES//1024//1024} MB)")

    raw = tmp_path.read_bytes()
    h = sha256_hex(raw)

    asset_dir = ensure_dir(ASSETS_ROOT / str(project_id) / "assets" / "plans" / h)
    original_dst = asset_dir / f"original{ext}"
    atomic_copy(tmp_path, original_dst)

    preview_png = None
    work_png = None
    if ftype == PlanFileType.PDF.value:
        page = int(pdf_page_index or 0)
        preview_png = _render_pdf_page_to_png(original_dst, page, preview_dpi)
        work_png = _render_pdf_page_to_png(original_dst, page, work_dpi)
    else:
        # for images: create preview/work resized
        preview_png = _normalize_image_to_png(original_dst, max_width=1400)
        work_png = _normalize_image_to_png(original_dst, max_width=2600)

    preview_path = asset_dir / "preview.png"
    work_path = asset_dir / "work.png"
    atomic_write_bytes(preview_path, preview_png)
    atomic_write_bytes(work_path, work_png)

    asset = PlanAsset(
        project_id=project_id,
        file_type=ftype,
        original_relpath=str(original_dst.relative_to(ASSETS_ROOT.parent)),
        original_hash=h,
        preview_relpath=str(preview_path.relative_to(ASSETS_ROOT.parent)),
        work_relpath=str(work_path.relative_to(ASSETS_ROOT.parent)),
        pdf_page_index=int(pdf_page_index or 0) if ftype == PlanFileType.PDF.value else None,
        preview_dpi=preview_dpi,
        work_dpi=work_dpi,
        created_at=datetime.utcnow(),
    )
    s.add(asset)
    s.flush()

    plan = Plan(project_id=project_id, name=plan_name, plan_asset_id=asset.id)
    s.add(plan)
    s.commit()
    s.refresh(plan)
    return plan

def list_plans(s: Session, project_id: int) -> list[Plan]:
    return list(s.execute(select(Plan).where(Plan.project_id == project_id).order_by(Plan.id.desc())).scalars().all())

def get_plan(s: Session, plan_id: int) -> Plan:
    return s.execute(select(Plan).where(Plan.id == plan_id)).scalar_one()

def set_plan_scale(s: Session, plan_id: int, scale_m_per_px: str) -> None:
    plan = get_plan(s, plan_id)
    plan.scale_m_per_px = scale_m_per_px
    s.commit()

def add_room(s: Session, plan_id: int, room_type: str, name: str | None, polygon_px: dict) -> PlanRoom:
    r = PlanRoom(plan_id=plan_id, room_type=room_type, name=name, polygon_px=polygon_px)
    s.add(r)
    s.commit()
    s.refresh(r)
    return r

def add_point(s: Session, plan_id: int, point_type: str, x_px: int, y_px: int, attributes: dict | None = None) -> PlanPoint:
    p = PlanPoint(plan_id=plan_id, point_type=point_type, x_px=x_px, y_px=y_px, attributes=attributes or {})
    s.add(p)
    s.commit()
    s.refresh(p)
    return p

def list_rooms(s: Session, plan_id: int) -> list[PlanRoom]:
    return list(s.execute(select(PlanRoom).where(PlanRoom.plan_id == plan_id).order_by(PlanRoom.id.desc())).scalars().all())

def list_points(s: Session, plan_id: int) -> list[PlanPoint]:
    return list(s.execute(select(PlanPoint).where(PlanPoint.plan_id == plan_id).order_by(PlanPoint.id.desc())).scalars().all())


def add_route(s: Session, plan_id: int, route_type: str, polyline_px: dict, attributes: dict | None = None) -> PlanRoute:
    r = PlanRoute(plan_id=plan_id, route_type=route_type, polyline_px=polyline_px, attributes=attributes or {})
    s.add(r)
    s.commit()
    s.refresh(r)
    return r

def list_routes(s: Session, plan_id: int) -> list[PlanRoute]:
    return list(s.execute(select(PlanRoute).where(PlanRoute.plan_id == plan_id).order_by(PlanRoute.id.desc())).scalars().all())

def delete_route(s: Session, route_id: int) -> None:
    r = s.execute(select(PlanRoute).where(PlanRoute.id == route_id)).scalar_one()
    s.delete(r)
    s.commit()

def compute_route_length_px(polyline_px: dict) -> float:
    pts = polyline_px.get("points") if isinstance(polyline_px, dict) else None
    if not isinstance(pts, list) or len(pts) < 2:
        return 0.0
    import math
    total = 0.0
    prev = pts[0]
    for p in pts[1:]:
        try:
            dx = float(p["x"]) - float(prev["x"])
            dy = float(p["y"]) - float(prev["y"])
        except Exception:
            continue
        total += math.sqrt(dx*dx + dy*dy)
        prev = p
    return total

def compute_plan_summary(s: Session, plan_id: int) -> dict:
    plan = get_plan(s, plan_id)
    rooms = list_rooms(s, plan_id)
    points = list_points(s, plan_id)
    routes = list_routes(s, plan_id)
    scale = None
    try:
        scale = float(plan.scale_m_per_px) if plan.scale_m_per_px else None
    except Exception:
        scale = None

    # point counts by type
    pt_counts = {}
    for p in points:
        pt_counts[p.point_type] = pt_counts.get(p.point_type, 0) + 1

    # route lengths
    route_rows = []
    total_m = 0.0
    for r in routes:
        px = compute_route_length_px(r.polyline_px)
        m = (px * scale) if (scale is not None) else None
        if m is not None:
            total_m += float(m)
        route_rows.append({
            "id": r.id,
            "route_type": r.route_type,
            "length_px": round(px, 1),
            "length_m": round(m, 2) if m is not None else None,
        })

    return {
        "plan_id": plan.id,
        "scale_m_per_px": plan.scale_m_per_px,
        "rooms_count": len(rooms),
        "points_count": len(points),
        "points_by_type": pt_counts,
        "routes_count": len(routes),
        "routes": route_rows,
        "routes_total_m": round(total_m, 2) if scale is not None else None,
    }


def compute_polygon_area_px2(polygon_px: dict) -> float:
    pts = polygon_px.get("points") if isinstance(polygon_px, dict) else None
    if not isinstance(pts, list) or len(pts) < 3:
        return 0.0
    # Shoelace formula
    area = 0.0
    n = len(pts)
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i+1) % n]
        try:
            x1 = float(p1["x"]); y1 = float(p1["y"])
            x2 = float(p2["x"]); y2 = float(p2["y"])
        except Exception:
            continue
        area += (x1 * y2) - (x2 * y1)
    return abs(area) / 2.0

def compute_room_areas(s: Session, plan_id: int) -> list[dict]:
    plan = get_plan(s, plan_id)
    rooms = list_rooms(s, plan_id)
    try:
        scale = float(plan.scale_m_per_px) if plan.scale_m_per_px else None
    except Exception:
        scale = None
    out=[]
    for r in rooms:
        px2 = compute_polygon_area_px2(r.polygon_px)
        m2 = (px2 * (scale**2)) if (scale is not None) else None
        out.append({
            "id": r.id,
            "name": r.name,
            "room_type": r.room_type,
            "area_px2": round(px2, 1),
            "area_m2": round(m2, 2) if m2 is not None else None,
        })
    return out

def compute_plan_quantities(s: Session, plan_id: int) -> dict:
    """Derives quantities from routes + points. Uses scale if available for meters."""
    plan = get_plan(s, plan_id)
    points = list_points(s, plan_id)
    routes = list_routes(s, plan_id)
    try:
        scale = float(plan.scale_m_per_px) if plan.scale_m_per_px else None
    except Exception:
        scale = None

    # point counts
    pt = {}
    for p in points:
        pt[p.point_type] = pt.get(p.point_type, 0) + 1

    # route lengths per type
    lengths_px = {}
    lengths_m = {}
    for r in routes:
        px = compute_route_length_px(r.polyline_px)
        lengths_px[r.route_type] = lengths_px.get(r.route_type, 0.0) + px
        if scale is not None:
            lengths_m[r.route_type] = lengths_m.get(r.route_type, 0.0) + (px * scale)

    # totals
    total_px = sum(lengths_px.values()) if lengths_px else 0.0
    total_m = sum(lengths_m.values()) if lengths_m else None

    return {
        "plan_id": plan.id,
        "scale_m_per_px": plan.scale_m_per_px,
        "points_by_type": pt,
        "routes_by_type_px": {k: round(v, 1) for k,v in lengths_px.items()},
        "routes_by_type_m": {k: round(v, 2) for k,v in lengths_m.items()} if scale is not None else {},
        "routes_total_px": round(total_px, 1),
        "routes_total_m": round(total_m, 2) if total_m is not None else None,
    }
