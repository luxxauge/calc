from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import urllib.parse

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from elektrocalc.settings import DB_URL, BASE_DIR, ASSETS_ROOT, IMPORTS_DIR
from elektrocalc.db.session import make_session_factory
from elektrocalc.db.enums import ProjectProfile, InstallType, RenovationDepth, VariantKey
from elektrocalc.db.models import CalcRun, CalcRunQuantity
from elektrocalc.services.projects import list_projects, create_project, get_project, update_project_inputs
from elektrocalc.services.plans import (
    create_plan_from_upload, list_plans, get_plan, list_rooms, list_points,
    set_plan_scale, add_room, add_point,
    add_route, list_routes, delete_route, compute_plan_summary, compute_plan_quantities, compute_room_areas,
)
from elektrocalc.services.calc import recalc_variant, list_calc_runs
from elektrocalc.services.core_config import get_or_create_initial_config_version
from elektrocalc.services.catalog import list_sheets, read_headers, guess_mapping, import_items_from_excel
from elektrocalc.services.lv import list_lv_documents, get_lv_document, list_positions, import_from_xlsx as lv_import_xlsx, import_from_csv as lv_import_csv, import_from_txt as lv_import_txt, set_match_manual, search_items
from elektrocalc.services.calc_engine import run_estimate, list_estimates, get_estimate, list_estimate_lines, summarize_estimate
from elektrocalc.services.param_preview import preview_param_extras
from elektrocalc.services.compare_export import build_compare_xlsx, build_compare_pdf
from elektrocalc.services.plan_mapping import seed_defaults_if_empty as seed_planmap_if_empty, list_mappings, upsert_mapping, delete_mapping
from elektrocalc.services.plan_to_calc import apply_plan_quantities_to_estimate
from elektrocalc.services.plan_export import build_quantities_xlsx, build_quantities_pdf
from elektrocalc.services.rate_card import get_default_card, list_lines as list_rate_lines, upsert_line as upsert_rate_line, delete_line as delete_rate_line, seed_defaults_if_empty as seed_ratecard_if_empty
from elektrocalc.services.param_rules import list_rules as list_param_rules, create_rule as create_param_rule, delete_rule as delete_param_rule, seed_defaults_if_empty as seed_param_rules_if_empty
from elektrocalc.services.labor_catalog import list_tasks, list_rules, create_task, delete_task, create_rule, delete_rule, seed_defaults_if_empty
from elektrocalc.services.inspection import (
    inspection_dashboard_data,
    create_tenant as create_inspection_tenant,
    create_customer as create_inspection_customer,
    create_object as create_inspection_object,
    add_distribution as create_inspection_distribution,
    create_inspection_order as create_inspection_order_entry,
    assign_distribution_to_order as assign_distribution_to_order_entry,
    create_defect as create_inspection_defect,
    create_appointment as create_inspection_appointment,
    create_measurement_set as create_inspection_measurement_set,
    create_measurement as create_inspection_measurement,
    create_report as create_inspection_report,
    update_report_status as update_inspection_report_status,
    create_distribution_report as create_inspection_distribution_report,
    update_inspection_order_status as update_inspection_order_status_entry,
    create_task as create_inspection_task,
    create_invoice as create_inspection_invoice,
    update_invoice_total as update_inspection_invoice_total,
    update_invoice_status as update_inspection_invoice_status,
    create_portal_release as create_inspection_portal_release,
    create_measuring_device as create_inspection_measuring_device,
    create_document_record as create_inspection_document_record,
    create_communication_entry as create_inspection_communication_entry,
    create_defect_deadline as create_inspection_defect_deadline,
    create_approval_step as create_inspection_approval_step,
    update_approval_step_status as update_inspection_approval_step_status,
    create_notification as create_inspection_notification,
    create_inspection_cycle as create_inspection_cycle_entry,
    create_backup_run as create_inspection_backup_run,
    create_thermography_entry as create_inspection_thermography_entry,
    create_device_calibration as create_inspection_device_calibration,
    create_number_sequence as create_inspection_number_sequence,
    issue_next_number as issue_inspection_number,
    create_payment_entry as create_inspection_payment_entry,
    create_data_retention_rule as create_inspection_retention_rule,
    create_restore_test as create_inspection_restore_test,
)
from elektrocalc.db.models import Item

def _build_lv_compare_data(s: Session, doc_id: int):
    variants = ["standard", "komfort", "premium"]
    doc = get_lv_document(s, doc_id)
    project = get_project(s, doc.project_id)

    # latest estimate per variant (list_estimates ordered desc id)
    est_all = list_estimates(s, doc_id)
    est_map = {v: None for v in variants}
    for e in est_all:
        v = (e.variant_key or "standard").lower()
        if v in est_map and est_map[v] is None:
            est_map[v] = e

    from elektrocalc.db.models import CalcExtraLine

    def totals_map_for_est(est):
        if est is None:
            return {}, []
        lines = list_estimate_lines(s, est.id)
        m = {int(l.lv_position_id): int(l.total_cent) for l in lines}
        extras = list(s.execute(select(CalcExtraLine).where(CalcExtraLine.estimate_id == est.id)).scalars().all())
        return m, extras

    stdm, std_extras = totals_map_for_est(est_map["standard"])
    komm, kom_extras = totals_map_for_est(est_map["komfort"])
    prem, pre_extras = totals_map_for_est(est_map["premium"])

    summaries = []
    for v in variants:
        est = est_map[v]
        if est is None:
            summaries.append({"variant": v, "material_cent": 0, "labor_cent": 0, "labor_minutes": 0, "total_cent": 0, "estimate_id": None})
            continue
        lines = list_estimate_lines(s, est.id)
        extras = list(s.execute(select(CalcExtraLine).where(CalcExtraLine.estimate_id == est.id)).scalars().all())
        summ = summarize_estimate(lines, extras)
        summaries.append({"variant": v, **summ, "estimate_id": est.id})

    positions = list_positions(s, doc_id)
    rows = []
    for p in positions:
        pid = int(p.id)
        rows.append({
            "pos_no": p.pos_no or "",
            "short_text": p.short_text or "",
            "std_total": stdm.get(pid, 0),
            "kom_total": komm.get(pid, 0),
            "pre_total": prem.get(pid, 0),
        })

    # Synthetic EXTRAS row
    rows.append({
        "pos_no": "EXTRAS",
        "short_text": "Parametrische Zusatzpositionen",
        "std_total": sum(int(x.total_cent) for x in std_extras) if std_extras else 0,
        "kom_total": sum(int(x.total_cent) for x in kom_extras) if kom_extras else 0,
        "pre_total": sum(int(x.total_cent) for x in pre_extras) if pre_extras else 0,
    })

    extras_by_variant = {"standard": std_extras, "komfort": kom_extras, "premium": pre_extras}

    return {
        "doc": doc,
        "project": project,
        "doc_name": doc.name,
        "project_name": project.name,
        "summaries": summaries,
        "rows": rows,
        "extras_by_variant": extras_by_variant,
    }


app = FastAPI(title="ElektroCalc Offline WebUI", docs_url=None, redoc_url=None)

templates = Jinja2Templates(directory=str(BASE_DIR / "elektrocalc" / "web" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "elektrocalc" / "web" / "static")), name="static")

SessionFactory = make_session_factory(DB_URL, echo=False)

@app.get("/", response_class=HTMLResponse)
def projects_page(request: Request):
    with SessionFactory() as s:
        get_or_create_initial_config_version(s)
        projects = list_projects(s)
    return templates.TemplateResponse("projects.html", {"request": request, "projects": projects, "profiles": [p.value for p in ProjectProfile]})
@app.get("/projects")
def projects_redirect():
    return RedirectResponse(url="/", status_code=303)


@app.post("/projects/create")
def projects_create(name: str = Form(...), customer_name: str | None = Form(None), profile: str = Form(ProjectProfile.EFH.value)):
    with SessionFactory() as s:
        p = create_project(s, name=name, customer_name=customer_name, profile=profile)
    return RedirectResponse(url=f"/projects/{p.id}", status_code=303)

@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail(request: Request, project_id: int):
    with SessionFactory() as s:
        p = get_project(s, project_id)
        inputs = p.inputs
    return templates.TemplateResponse(
        "project_detail.html",
        {"request": request, "project": p, "inputs": inputs, "install_types": [e.value for e in InstallType], "reno_depths": [e.value for e in RenovationDepth]},
    )

@app.post("/projects/{project_id}/inputs")
def project_inputs_save(project_id: int,
                        area_m2: str = Form(...),
                        floors: int = Form(...),
                        room_height_m: str = Form(...),
                        install_type: str = Form(...),
                        renovation_depth: str = Form(...),
                        distribution_factor: str = Form(...),
                        layout_factor: str = Form(...),
                        rooms_total: str | None = Form(None),
                        bathrooms: str | None = Form(None),
                        ):
    data = {
        "area_m2": area_m2,
        "floors": floors,
        "room_height_m": room_height_m,
        "install_type": install_type,
        "renovation_depth": renovation_depth,
        "distribution_factor": distribution_factor,
        "layout_factor": layout_factor,
        "rooms_total": int(rooms_total) if rooms_total else None,
        "bathrooms": int(bathrooms) if bathrooms else None,
    }
    with SessionFactory() as s:
        update_project_inputs(s, project_id, data)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.get("/projects/{project_id}/variants", response_class=HTMLResponse)
def variants_page(request: Request, project_id: int):
    variants = [VariantKey.STANDARD.value, VariantKey.KOMFORT.value, VariantKey.PREMIUM.value]
    with SessionFactory() as s:
        p = get_project(s, project_id)
        runs = {v: list_calc_runs(s, project_id, v) for v in variants}
    return templates.TemplateResponse("variants.html", {"request": request, "project": p, "variants": variants, "runs": runs})

@app.post("/projects/{project_id}/variants/{variant_key}/recalc")
def variants_recalc(project_id: int, variant_key: str):
    with SessionFactory() as s:
        recalc_variant(s, project_id, variant_key)
    return RedirectResponse(url=f"/projects/{project_id}/variants", status_code=303)

@app.get("/calc/{calc_run_id}", response_class=HTMLResponse)
def calc_detail(request: Request, calc_run_id: int):
    with SessionFactory() as s:
        run = s.get(CalcRun, calc_run_id)
        if not run:
            return HTMLResponse("Not found", status_code=404)
        project = get_project(s, run.project_id)
        from sqlalchemy import select
        qtys = list(s.execute(select(CalcRunQuantity).where(CalcRunQuantity.calc_run_id == calc_run_id)).scalars().all())
    return templates.TemplateResponse("calc_detail.html", {"request": request, "run": run, "project": project, "qtys": qtys})

@app.get("/projects/{project_id}/plans", response_class=HTMLResponse)
def plans_page(request: Request, project_id: int):
    with SessionFactory() as s:
        p = get_project(s, project_id)
        plans = list_plans(s, project_id)
    return templates.TemplateResponse("plans.html", {"request": request, "project": p, "plans": plans})

@app.post("/projects/{project_id}/plans/upload")
async def plans_upload(project_id: int,
                       plan_name: str = Form(...),
                       pdf_page_index: int | None = Form(None),
                       file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        with SessionFactory() as s:
            create_plan_from_upload(s, project_id, file.filename, tmp_path, plan_name=plan_name, pdf_page_index=pdf_page_index)
    finally:
        try: tmp_path.unlink(missing_ok=True)
        except Exception: pass
    return RedirectResponse(url=f"/projects/{project_id}/plans", status_code=303)
@app.get("/plans/{plan_id}/quantities.xlsx")
def plan_quantities_xlsx(plan_id: int):
    with SessionFactory() as s:
        plan = get_plan(s, plan_id)
        project = get_project(s, plan.project_id)
        quantities = compute_plan_quantities(s, plan_id)
        room_areas = compute_room_areas(s, plan_id)
        content = build_quantities_xlsx(plan.name, project.name, quantities, room_areas)
    filename = f"plan_quantities_{plan_id}.xlsx"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/plans/{plan_id}/quantities.pdf")
def plan_quantities_pdf(plan_id: int):
    with SessionFactory() as s:
        plan = get_plan(s, plan_id)
        project = get_project(s, plan.project_id)
        quantities = compute_plan_quantities(s, plan_id)
        room_areas = compute_room_areas(s, plan_id)
        content = build_quantities_pdf(plan.name, project.name, quantities, room_areas)
    filename = f"plan_quantities_{plan_id}.pdf"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/plans/{plan_id}/editor", response_class=HTMLResponse)
def plan_editor(request: Request, plan_id: int):
    with SessionFactory() as s:
        plan = get_plan(s, plan_id)
        project = get_project(s, plan.project_id)
        rooms = list_rooms(s, plan_id)
        points = list_points(s, plan_id)
        try:
            routes = list_routes(s, plan_id)
        except Exception:
            routes = []
        summary = compute_plan_summary(s, plan_id)
    return templates.TemplateResponse("plan_editor.html", {"request": request, "plan": plan, "project": project, "rooms": rooms, "points": points, "routes": routes, "summary": summary})

@app.get("/plans/{plan_id}/raster/{kind}")
def plan_raster(plan_id: int, kind: str):
    if kind not in ("preview", "work"):
        return JSONResponse({"error":"kind must be preview|work"}, status_code=400)
    with SessionFactory() as s:
        plan = get_plan(s, plan_id)
        asset = plan.asset
        rel = asset.preview_relpath if kind=="preview" else asset.work_relpath
        if not rel:
            return JSONResponse({"error":"raster not available"}, status_code=404)
        fpath = (ASSETS_ROOT.parent / rel).resolve()
        return FileResponse(fpath.as_posix(), media_type="image/png")


@app.get("/catalog", response_class=HTMLResponse)
def catalog_page(request: Request):
    with SessionFactory() as s:
        items = list(s.execute(__import__("sqlalchemy").select(Item).order_by(Item.id.desc()).limit(200)).scalars().all())
    return templates.TemplateResponse("catalog.html", {"request": request, "items": items})

@app.post("/catalog/import/start")
async def catalog_import_start(request: Request, file: UploadFile = File(...), source: str | None = Form(None)):
    # persist upload to data/imports/<uuid>.xlsx
    if not file.filename.lower().endswith(".xlsx"):
        return HTMLResponse("Nur .xlsx erlaubt", status_code=400)
    import_id = str(__import__("uuid").uuid4())
    dst = IMPORTS_DIR / f"{import_id}.xlsx"
    raw = await file.read()
    dst.write_bytes(raw)
    # default mapping: first sheet
    sheets = list_sheets(dst)
    sheet = sheets[0] if sheets else "Sheet1"
    return RedirectResponse(url=f"/catalog/import/map?import_id={import_id}&sheet={urllib.parse.quote(sheet)}&source={urllib.parse.quote(source or '')}", status_code=303)

@app.get("/catalog/import/map", response_class=HTMLResponse)
def catalog_import_map(request: Request, import_id: str, sheet: str, source: str | None = None):
    path = IMPORTS_DIR / f"{import_id}.xlsx"
    if not path.exists():
        return HTMLResponse("Import-Datei nicht gefunden.", status_code=404)
    sheets = list_sheets(path)
    if sheet not in sheets and sheets:
        sheet = sheets[0]
    headers = read_headers(path, sheet, header_row=1)
    mapping = guess_mapping(headers)
    fields = [
        ("article_no", "Artikelnummer"),
        ("name", "Name/Bezeichnung"),
        ("description", "Beschreibung"),
        ("manufacturer", "Hersteller"),
        ("category", "Kategorie"),
        ("unit", "Einheit"),
        ("price_ek", "EK (netto)"),
        ("price_vk", "VK (netto)"),
        ("vat_rate", "MwSt/VAT"),
    ]
    required = {"article_no", "name"}
    return templates.TemplateResponse(
        "catalog_import_map.html",
        {
            "request": request,
            "import_id": import_id,
            "filename": path.name,
            "sheets": sheets,
            "sheet": sheet,
            "headers": [h for h in headers if h],
            "mapping": mapping,
            "fields": fields,
            "required": required,
            "source": source,
        },
    )

@app.post("/catalog/import/commit")
def catalog_import_commit(
    import_id: str = Form(...),
    sheet: str = Form(...),
    header_row: int = Form(1),
    start_row: int = Form(2),
    source: str | None = Form(None),
    **formdata
):
    # collect mapping from form fields map__*
    mapping = {}
    for k, v in formdata.items():
        if k.startswith("map__"):
            mapping[k.replace("map__", "")] = v or None

    if not mapping.get("article_no") or not mapping.get("name"):
        return HTMLResponse("Mapping unvollständig: Artikelnummer und Name sind Pflicht.", status_code=400)

    path = IMPORTS_DIR / f"{import_id}.xlsx"
    if not path.exists():
        return HTMLResponse("Import-Datei nicht gefunden.", status_code=404)

    with SessionFactory() as s:
        stats = import_items_from_excel(s, path, sheet=sheet, mapping=mapping, header_row=int(header_row), start_row=int(start_row), source=source)

    # Optional: keep file for audit, but we can delete it to save space.
    try:
        path.unlink()
    except Exception:
        pass

    return RedirectResponse(url="/catalog", status_code=303)


# ---------------- LV / Ausschreibung ----------------

@app.get("/projects/{project_id}/lv", response_class=HTMLResponse)
def lv_list_page(request: Request, project_id: int):
    with SessionFactory() as s:
        project = get_project(s, project_id)
        docs = list_lv_documents(s, project_id)
    return templates.TemplateResponse("lv_list.html", {"request": request, "project": project, "docs": docs})

@app.post("/projects/{project_id}/lv/import/start")
async def lv_import_start(project_id: int, name: str = Form(...), csv_delim: str = Form(";"), file: UploadFile = File(...)):
    fn = file.filename or "upload"
    ext = Path(fn).suffix.lower()
    import_id = str(__import__("uuid").uuid4())
    dst = IMPORTS_DIR / f"lv_{import_id}{ext}"
    raw = await file.read()
    dst.write_bytes(raw)

    if ext == ".xlsx":
        sheets = list_sheets(dst)
        sheet = sheets[0] if sheets else "Sheet1"
        return RedirectResponse(url=f"/projects/{project_id}/lv/import/map?import_id={import_id}&source_type=xlsx&sheet={urllib.parse.quote(sheet)}&name={urllib.parse.quote(name)}", status_code=303)
    if ext == ".csv":
        return RedirectResponse(url=f"/projects/{project_id}/lv/import/map?import_id={import_id}&source_type=csv&name={urllib.parse.quote(name)}&csv_delim={urllib.parse.quote(csv_delim or ';')}", status_code=303)
    if ext == ".txt":
        return RedirectResponse(url=f"/projects/{project_id}/lv/import/map?import_id={import_id}&source_type=txt&name={urllib.parse.quote(name)}", status_code=303)

    try:
        dst.unlink()
    except Exception:
        pass
    return HTMLResponse("Nicht unterstützt. Nur xlsx/csv/txt.", status_code=400)

@app.get("/projects/{project_id}/lv/import/map", response_class=HTMLResponse)
def lv_import_map(request: Request, project_id: int, import_id: str, source_type: str, name: str, sheet: str | None = None, csv_delim: str = ";"):
    with SessionFactory() as s:
        project = get_project(s, project_id)

    fields = [
        ("pos_no", "Positionsnummer"),
        ("short_text", "Kurztext"),
        ("long_text", "Langtext"),
        ("qty", "Menge"),
        ("unit", "Einheit"),
    ]
    required = {"short_text"}

    if source_type == "xlsx":
        path = IMPORTS_DIR / f"lv_{import_id}.xlsx"
        if not path.exists():
            return HTMLResponse("Import-Datei nicht gefunden.", status_code=404)
        sheets = list_sheets(path)
        if not sheet or sheet not in sheets:
            sheet = sheets[0] if sheets else "Sheet1"
        headers = read_headers(path, sheet, header_row=1)
        # quick guess
        mapping = {"pos_no": None, "short_text": None, "long_text": None, "qty": None, "unit": None}
        for h in headers:
            hn = h.lower()
            if mapping["pos_no"] is None and ("pos" in hn or "nr" in hn):
                mapping["pos_no"] = h
            if mapping["short_text"] is None and ("kurz" in hn or "text" in hn or "bezeich" in hn or "titel" in hn):
                mapping["short_text"] = h
            if mapping["qty"] is None and ("menge" in hn or "qty" in hn or "anz" in hn):
                mapping["qty"] = h
            if mapping["unit"] is None and ("einheit" in hn or "meh" in hn or "unit" in hn):
                mapping["unit"] = h
            if mapping["long_text"] is None and ("lang" in hn or "beschreibung" in hn):
                mapping["long_text"] = h
        return templates.TemplateResponse("lv_import_map.html", {
            "request": request, "project": project, "import_id": import_id, "source_type": "xlsx",
            "filename": path.name, "sheets": sheets, "sheet": sheet,
            "headers": [h for h in headers if h], "mapping": mapping, "fields": fields, "required": required,
            "lv_name": name, "csv_delim": csv_delim,
        })

    if source_type == "csv":
        path = IMPORTS_DIR / f"lv_{import_id}.csv"
        if not path.exists():
            return HTMLResponse("Import-Datei nicht gefunden.", status_code=404)
        import csv as _csv
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = _csv.reader(f, delimiter=csv_delim or ";")
            headers = next(reader, [])
        headers = [str(h).strip() for h in headers if h is not None]
        mapping = {"pos_no": None, "short_text": None, "long_text": None, "qty": None, "unit": None}
        for h in headers:
            hn = h.lower()
            if mapping["pos_no"] is None and ("pos" in hn or "nr" in hn):
                mapping["pos_no"] = h
            if mapping["short_text"] is None and ("kurz" in hn or "text" in hn or "bezeich" in hn or "titel" in hn):
                mapping["short_text"] = h
            if mapping["qty"] is None and ("menge" in hn or "qty" in hn or "anz" in hn):
                mapping["qty"] = h
            if mapping["unit"] is None and ("einheit" in hn or "meh" in hn or "unit" in hn):
                mapping["unit"] = h
            if mapping["long_text"] is None and ("lang" in hn or "beschreibung" in hn):
                mapping["long_text"] = h
        return templates.TemplateResponse("lv_import_map.html", {
            "request": request, "project": project, "import_id": import_id, "source_type": "csv",
            "filename": path.name, "headers": headers, "mapping": mapping, "fields": fields, "required": required,
            "lv_name": name, "csv_delim": csv_delim, "sheets": [], "sheet": "",
        })

    # txt
    path = IMPORTS_DIR / f"lv_{import_id}.txt"
    if not path.exists():
        return HTMLResponse("Import-Datei nicht gefunden.", status_code=404)
    return templates.TemplateResponse("lv_import_map.html", {
        "request": request, "project": project, "import_id": import_id, "source_type": "txt",
        "filename": path.name, "headers": [], "mapping": {"pos_no": None, "short_text": None, "long_text": None, "qty": None, "unit": None},
        "fields": fields, "required": required, "lv_name": name, "csv_delim": csv_delim, "sheets": [], "sheet": "",
    })

@app.post("/projects/{project_id}/lv/import/commit")
def lv_import_commit(
    project_id: int,
    import_id: str = Form(...),
    source_type: str = Form(...),
    name: str = Form(...),
    csv_delim: str = Form(";"),
    sheet: str | None = Form(None),
    header_row: int = Form(1),
    start_row: int = Form(2),
    **formdata
):
    mapping = {}
    for k, v in formdata.items():
        if k.startswith("map__"):
            mapping[k.replace("map__", "")] = v or None

    with SessionFactory() as s:
        if source_type == "xlsx":
            path = IMPORTS_DIR / f"lv_{import_id}.xlsx"
            if not path.exists():
                return HTMLResponse("Import-Datei nicht gefunden.", status_code=404)
            if not mapping.get("short_text"):
                return HTMLResponse("Mapping unvollständig: Kurztext ist Pflicht.", status_code=400)
            doc = lv_import_xlsx(s, project_id, name=name, xlsx_path=path, sheet=sheet or list_sheets(path)[0], mapping=mapping, header_row=int(header_row), start_row=int(start_row), filename=path.name)
            try: path.unlink()
            except Exception: pass
            return RedirectResponse(url=f"/lv/{doc.id}", status_code=303)

        if source_type == "csv":
            path = IMPORTS_DIR / f"lv_{import_id}.csv"
            if not path.exists():
                return HTMLResponse("Import-Datei nicht gefunden.", status_code=404)
            if not mapping.get("short_text"):
                return HTMLResponse("Mapping unvollständig: Kurztext ist Pflicht.", status_code=400)
            doc = lv_import_csv(s, project_id, name=name, csv_path=path, mapping=mapping, delimiter=(csv_delim or ";"), filename=path.name)
            try: path.unlink()
            except Exception: pass
            return RedirectResponse(url=f"/lv/{doc.id}", status_code=303)

        if source_type == "txt":
            path = IMPORTS_DIR / f"lv_{import_id}.txt"
            if not path.exists():
                return HTMLResponse("Import-Datei nicht gefunden.", status_code=404)
            text = path.read_text(encoding="utf-8", errors="ignore")
            doc = lv_import_txt(s, project_id, name=name, text=text, filename=path.name)
            try: path.unlink()
            except Exception: pass
            return RedirectResponse(url=f"/lv/{doc.id}", status_code=303)

    return HTMLResponse("Unknown source_type", status_code=400)

@app.get("/lv/{doc_id}", response_class=HTMLResponse)
def lv_doc_page(request: Request, doc_id: int):
    with SessionFactory() as s:
        doc = get_lv_document(s, doc_id)
        project = get_project(s, doc.project_id)
        positions = list_positions(s, doc_id)
    return templates.TemplateResponse("lv_doc.html", {"request": request, "doc": doc, "project": project, "positions": positions})

@app.get("/lv/{doc_id}/match", response_class=HTMLResponse)
def lv_match_page(request: Request, doc_id: int):
    with SessionFactory() as s:
        doc = get_lv_document(s, doc_id)
        project = get_project(s, doc.project_id)
        positions = list_positions(s, doc_id)
    return templates.TemplateResponse("lv_match.html", {"request": request, "doc": doc, "project": project, "positions": positions})


# ---------------- Kalkulation ----------------

@app.get("/lv/{doc_id}/calc", response_class=HTMLResponse)
def lv_calc_page(request: Request, doc_id: int):
    with SessionFactory() as s:
        doc = get_lv_document(s, doc_id)
        project = get_project(s, doc.project_id)
        estimates = list_estimates(s, doc_id)
        plans = list_plans(s, doc.project_id)
    return templates.TemplateResponse("lv_calc.html", {"request": request, "doc": doc, "project": project, "estimates": estimates, "plans": plans})


@app.get("/lv/{doc_id}/compare", response_class=HTMLResponse)
def lv_compare_page(request: Request, doc_id: int):
    variants = ["standard", "komfort", "premium"]
    with SessionFactory() as s:
        doc = get_lv_document(s, doc_id)
        project = get_project(s, doc.project_id)

        # latest estimate per variant
        est_all = list_estimates(s, doc_id)
        est_map = {v: None for v in variants}
        for e in est_all:
            v = (e.variant_key or "standard").lower()
            if v in est_map and est_map[v] is None:
                est_map[v] = e

        from elektrocalc.db.models import CalcExtraLine

        summaries = []
        # position totals maps
        stdm, komm, prem = {}, {}, {}

        # helper: build totals map for estimate lines
        def totals_map_for_est(est):
            if est is None:
                return {}, []
            lines = list_estimate_lines(s, est.id)
            m = {}
            for l in lines:
                m[int(l.lv_position_id)] = int(l.total_cent)
            extras = list(s.execute(select(CalcExtraLine).where(CalcExtraLine.estimate_id==est.id)).scalars().all())
            return m, extras

        stdm, std_extras = totals_map_for_est(est_map["standard"])
        komm, kom_extras = totals_map_for_est(est_map["komfort"])
        prem, pre_extras = totals_map_for_est(est_map["premium"])

        # Summaries (including extras)
        for v in variants:
            est = est_map[v]
            if est is None:
                summaries.append({"variant": v, "material_cent": 0, "labor_cent": 0, "labor_minutes": 0, "total_cent": 0, "estimate_id": None})
                continue
            lines = list_estimate_lines(s, est.id)
            extras = list(s.execute(select(CalcExtraLine).where(CalcExtraLine.estimate_id==est.id)).scalars().all())
            summ = summarize_estimate(lines, extras)
            summaries.append({"variant": v, **summ, "estimate_id": est.id})

        # Positions
        positions = list_positions(s, doc_id)
        pos_map = {p.id: p for p in positions}

        rows = []
        for pid, p in pos_map.items():
            rows.append({
                "pos_no": p.pos_no or "",
                "short_text": p.short_text or "",
                "std_total": stdm.get(pid, 0),
                "kom_total": komm.get(pid, 0),
                "pre_total": prem.get(pid, 0),
            })

        # Synthetic extras row for transparency in delta table
        rows.append({
            "pos_no": "EXTRAS",
            "short_text": "Parametrische Zusatzpositionen",
            "std_total": sum(int(x.total_cent) for x in std_extras) if std_extras else 0,
            "kom_total": sum(int(x.total_cent) for x in kom_extras) if kom_extras else 0,
            "pre_total": sum(int(x.total_cent) for x in pre_extras) if pre_extras else 0,
        })

        # Optional: breakdown lists for template
        extras_by_variant = {
            "standard": std_extras,
            "komfort": kom_extras,
            "premium": pre_extras,
        }

    # CSV export
@app.get("/lv/{doc_id}/compare.csv")
def lv_compare_csv(doc_id: int):
    variants = ["standard","komfort","premium"]
    import csv, io
    with SessionFactory() as s:
        doc = get_lv_document(s, doc_id)
        est_all = list_estimates(s, doc_id)
        est_map = {v: None for v in variants}
        for e in est_all:
            v=(e.variant_key or "standard").lower()
            if v in est_map and est_map[v] is None:
                est_map[v]=e

        from elektrocalc.db.models import CalcExtraLine
        rows=[]
        for v in variants:
            est=est_map[v]
            if not est: continue
            lines=list_estimate_lines(s, est.id)
            extras=list(s.execute(select(CalcExtraLine).where(CalcExtraLine.estimate_id==est.id)).scalars().all())
            summ=summarize_estimate(lines, extras)
            rows.append([v, summ["material_cent"]/100, summ["labor_cent"]/100, summ["total_cent"]/100])

    buf=io.StringIO()
    w=csv.writer(buf, delimiter=";")
    w.writerow(["Variante","Material €","Lohn €","Gesamt €"])
    for r in rows: w.writerow(r)
    return Response(buf.getvalue(), media_type="text/csv")
@app.get("/lv/{doc_id}/compare.xlsx")
def lv_compare_export_xlsx(doc_id: int):
    with SessionFactory() as s:
        data = _build_lv_compare_data(s, doc_id)
        content = build_compare_xlsx(data)
    filename = f"lv_compare_{doc_id}.xlsx"
    return StreamingResponse(BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })

@app.get("/lv/{doc_id}/compare.pdf")
def lv_compare_export_pdf(doc_id: int):
    with SessionFactory() as s:
        data = _build_lv_compare_data(s, doc_id)
        content = build_compare_pdf(data)
    filename = f"lv_compare_{doc_id}.pdf"
    return StreamingResponse(BytesIO(content), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })


@app.post("/lv/{doc_id}/calc/run")
def lv_calc_run(
    doc_id: int,
    variant: str = Form(...),
    labor_rate_eur: str = Form("65"),
    overhead_pct: str = Form("0.15"),
    profit_pct: str = Form("0.10"),
):
    # convert €/h to cent
    try:
        lr = int((float(str(labor_rate_eur).replace(",", ".")) * 100))
    except Exception:
        return HTMLResponse("Stundensatz ungültig", status_code=400)
    with SessionFactory() as s:
        est = run_estimate(s, lv_document_id=doc_id, variant=variant, labor_rate_cent=lr, overhead_pct=overhead_pct, profit_pct=profit_pct)
    return RedirectResponse(url=f"/calc/{est.id}", status_code=303)
@app.post("/lv/{doc_id}/calc/run_all")
def lv_calc_run_all(doc_id: int):
    variants = ["standard", "komfort", "premium"]
    with SessionFactory() as s:
        for v in variants:
            run_estimate(s, doc_id, variant=v)
    return RedirectResponse(url=f"/lv/{doc_id}/compare", status_code=303)

@app.post("/lv/{doc_id}/calc/apply_plan")
@app.post("/lv/{doc_id}/calc/apply_plan")
def lv_calc_apply_plan(
    doc_id: int,
    plan_id: int = Form(...),
    variant: str = Form("komfort"),
    apply_all_variants: str = Form(""),
):
    with SessionFactory() as s:
        doc = get_lv_document(s, doc_id)
        project = get_project(s, doc.project_id)
        plan = get_plan(s, plan_id)
        if plan.project_id != project.id:
            # Prevent accidental cross-project usage
            raise HTTPException(status_code=400, detail="Plan gehört nicht zu diesem Projekt.")

        inp = project.inputs
        try:
            eur_h = float(str(inp.labor_rate_eur_h).replace(",", "."))
        except Exception:
            eur_h = 72.0
        labor_rate_per_min_cent = int(round((eur_h * 100) / 60.0))

        variants = ["standard", "komfort", "premium"] if apply_all_variants.strip() else [variant]
        for v in variants:
            est = run_estimate(s, doc_id, variant=v)
            apply_plan_quantities_to_estimate(
                s,
                project_id=project.id,
                plan_id=plan_id,
                estimate_id=est.id,
                variant=v,
                labor_rate_per_min_cent=labor_rate_per_min_cent,
                overhead_pct=inp.overhead_pct or "0",
                profit_pct=inp.profit_pct or "0",
            )
    return RedirectResponse(url=f"/lv/{doc_id}/compare", status_code=303)


@app.get("/calc/{estimate_id}", response_class=HTMLResponse)
def calc_detail_page(request: Request, estimate_id: int):
    with SessionFactory() as s:
        est = get_estimate(s, estimate_id)
        doc = get_lv_document(s, est.lv_document_id)
        project = get_project(s, doc.project_id)
        lines = list_estimate_lines(s, estimate_id)
        from elektrocalc.db.models import CalcExtraLine
        extras = list(s.execute(select(CalcExtraLine).where(CalcExtraLine.estimate_id==estimate_id)).scalars().all())
        summary = summarize_estimate(lines, extras)
        # join with positions for display
        from elektrocalc.db.models import LvPosition
        pos_map = {p.id: p for p in s.execute(select(LvPosition).where(LvPosition.lv_document_id==doc.id)).scalars().all()}
        rows = []
        for l in lines:
            p = pos_map.get(l.lv_position_id)
            rows.append({
                "pos_no": p.pos_no if p else "",
                "short_text": p.short_text if p else "",
                "qty": l.qty,
                "unit": l.unit,
                "material_cent": l.material_cent,
                "labor_minutes": l.labor_minutes,
                "labor_source": getattr(l, "labor_source", "heuristic"),
                "labor_task_code": getattr(l, "labor_task_code", None),
                "labor_rule_info": getattr(l, "labor_rule_info", None),
                "labor_cent": l.labor_cent,
                "total_cent": l.total_cent,
            })
    return templates.TemplateResponse("calc_detail.html", {"request": request, "est": est, "doc": doc, "project": project, "rows": rows, "summary": summary, "extras": extras})


# ---------------- Zeitkatalog ----------------

@app.get("/labor", response_class=HTMLResponse)
def labor_page(request: Request, error: str | None = None):
    with SessionFactory() as s:
        tasks = list_tasks(s)
        rules = list_rules(s)
    return templates.TemplateResponse("labor.html", {"request": request, "tasks": tasks, "rules": rules, "error": error})

@app.post("/labor/tasks/create")
def labor_task_create(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    unit: str = Form("pcs"),
    minutes_per_unit: str = Form("10"),
    notes: str | None = Form(None),
):
    try:
        mpu = int(float(str(minutes_per_unit).replace(",", ".")))
    except Exception:
        return RedirectResponse(url="/labor?error=Minuten%20ung%C3%BCltig", status_code=303)
    try:
        with SessionFactory() as s:
            create_task(s, code=code, name=name, unit=unit, minutes_per_unit=mpu, notes=notes)
    except Exception as e:
        return RedirectResponse(url=f"/labor?error={urllib.parse.quote(str(e))}", status_code=303)
    return RedirectResponse(url="/labor", status_code=303)

@app.post("/labor/tasks/{task_id}/delete")
def labor_task_delete(task_id: int):
    with SessionFactory() as s:
        delete_task(s, task_id)
    return RedirectResponse(url="/labor", status_code=303)

@app.post("/labor/rules/create")
def labor_rule_create(
    pattern: str = Form(...),
    is_regex: str | None = Form(None),
    priority: str = Form("100"),
    task_id: int = Form(...),
    enabled: str | None = Form(None),
):
    try:
        prio = int(priority)
    except Exception:
        return RedirectResponse(url="/labor?error=Priorit%C3%A4t%20ung%C3%BCltig", status_code=303)
    try:
        with SessionFactory() as s:
            create_rule(s, pattern=pattern, is_regex=bool(is_regex), priority=prio, task_id=task_id, enabled=bool(enabled))
    except Exception as e:
        return RedirectResponse(url=f"/labor?error={urllib.parse.quote(str(e))}", status_code=303)
    return RedirectResponse(url="/labor", status_code=303)

@app.post("/labor/rules/{rule_id}/delete")
def labor_rule_delete(rule_id: int):
    with SessionFactory() as s:
        delete_rule(s, rule_id)
    return RedirectResponse(url="/labor", status_code=303)


# ---------------- Rate Card ----------------

@app.get("/ratecard", response_class=HTMLResponse)
def ratecard_page(request: Request, error: str | None = None):
    with SessionFactory() as s:
        card = get_default_card(s)
        lines = list_rate_lines(s, card.id)
    return templates.TemplateResponse("rate_card.html", {"request": request, "card": card, "lines": lines, "error": error})

@app.post("/ratecard/lines/new")
def ratecard_new_line(
    key: str = Form(...),
    description: str = Form(""),
    unit: str = Form("pcs"),
    material_eur: str = Form("0"),
    labor_task_code: str | None = Form(None),
    item_id: str | None = Form(None),
):
    try:
        eur = float(str(material_eur).replace(",", "."))
        muc = int(round(eur * 100))
    except Exception:
        return RedirectResponse(url="/ratecard?error=Material%20ung%C3%BCltig", status_code=303)
    iid = None
    try:
        if item_id and str(item_id).strip():
            iid = int(str(item_id).strip())
    except Exception:
        return RedirectResponse(url="/ratecard?error=Item-ID%20ung%C3%BCltig", status_code=303)

    with SessionFactory() as s:
        card = get_default_card(s)
        try:
            upsert_rate_line(s, card.id, key=key, description=description, unit=unit, material_unit_cent=muc, labor_task_code=labor_task_code, item_id=iid)
        except Exception as e:
            return RedirectResponse(url=f"/ratecard?error={urllib.parse.quote(str(e))}", status_code=303)
    return RedirectResponse(url="/ratecard", status_code=303)

@app.post("/ratecard/lines/{line_id}/upsert")
def ratecard_upsert_line(
    line_id: int,
    key: str = Form(...),
    description: str = Form(""),
    unit: str = Form("pcs"),
    material_eur: str = Form("0"),
    labor_task_code: str | None = Form(None),
    item_id: str | None = Form(None),
):
    try:
        eur = float(str(material_eur).replace(",", "."))
        muc = int(round(eur * 100))
    except Exception:
        return RedirectResponse(url="/ratecard?error=Material%20ung%C3%BCltig", status_code=303)
    iid = None
    try:
        if item_id and str(item_id).strip():
            iid = int(str(item_id).strip())
    except Exception:
        return RedirectResponse(url="/ratecard?error=Item-ID%20ung%C3%BCltig", status_code=303)

    with SessionFactory() as s:
        card = get_default_card(s)
        # line_id not used for now; upsert by key
        try:
            upsert_rate_line(s, card.id, key=key, description=description, unit=unit, material_unit_cent=muc, labor_task_code=labor_task_code, item_id=iid)
        except Exception as e:
            return RedirectResponse(url=f"/ratecard?error={urllib.parse.quote(str(e))}", status_code=303)
    return RedirectResponse(url="/ratecard", status_code=303)

@app.post("/ratecard/lines/{line_id}/delete")
def ratecard_delete_line(line_id: int):
    with SessionFactory() as s:
        delete_rate_line(s, line_id)
    return RedirectResponse(url="/ratecard", status_code=303)


# ---------------- Param Rules ----------------

@app.get("/paramrules", response_class=HTMLResponse)
def param_rules_page(request: Request, error: str | None = None):
    with SessionFactory() as s:
        rules = list_param_rules(s)
    return templates.TemplateResponse("param_rules.html", {"request": request, "rules": rules, "error": error})

@app.post("/paramrules/create")
def param_rules_create(
    variant_key: str = Form("komfort"),
    building_type: str = Form("any"),
    priority: str = Form("100"),
    enabled: str | None = Form(None),
    rate_key: str = Form(...),
    description_tpl: str = Form("{rate_key} (param)"),
    unit: str = Form("pcs"),
    qty_expr: str = Form("0"),
    note: str | None = Form(None),
):
    try:
        prio = int(priority)
    except Exception:
        return RedirectResponse(url="/paramrules?error=Priorit%C3%A4t%20ung%C3%BCltig", status_code=303)
    with SessionFactory() as s:
        # validate qty_expr (safe) and rate_key existence
        try:
            _ = safe_eval(qty_expr, {"area_m2": 100.0, "rooms": 4, "floors": 2, "apartments": 1})
        except Exception as e:
            return RedirectResponse(url=f"/paramrules?error={urllib.parse.quote('Expr ungültig: ' + str(e))}", status_code=303)
        if lookup_line(s, rate_key) is None:
            return RedirectResponse(url=f"/paramrules?error={urllib.parse.quote('Rate-Key nicht in Rate Card: ' + rate_key)}", status_code=303)
        try:
            create_param_rule(
                s,
                variant_key=variant_key,
                building_type=building_type,
                enabled=bool(enabled),
                priority=prio,
                rate_key=rate_key,
                description_tpl=description_tpl,
                unit=unit,
                qty_expr=qty_expr,
                note=note,
            )
        except Exception as e:
            return RedirectResponse(url=f"/paramrules?error={urllib.parse.quote(str(e))}", status_code=303)
    return RedirectResponse(url="/paramrules", status_code=303)

@app.post("/paramrules/{rule_id}/delete")
def param_rules_delete(rule_id: int):
    with SessionFactory() as s:
        delete_param_rule(s, rule_id)
    return RedirectResponse(url="/paramrules", status_code=303)


# ---------------- Param Preview ----------------

@app.get("/parampreview", response_class=HTMLResponse)
def param_preview_page(
    request: Request,
    variant: str = "komfort",
    building_type: str = "efh",
    area_m2: str = "100",
    rooms: int = 4,
    floors: int = 2,
    apartments: int = 1,
):
    # fixed labor rate for preview; can be made configurable later
    labor_rate_per_min_cent = 120  # 72 €/h
    try:
        area = float(str(area_m2).replace(",", "."))
    except Exception:
        area = 0.0
    with SessionFactory() as s:
        extras, checks = preview_param_extras(
            s,
            variant=variant,
            building_type=building_type,
            area_m2=area,
            rooms=int(rooms or 0),
            floors=int(floors or 1),
            apartments=int(apartments or 0),
            labor_rate_per_min_cent=labor_rate_per_min_cent,
            overhead_pct="0",
            profit_pct="0",
        )
    return templates.TemplateResponse("param_preview.html", {
        "request": request,
        "variant": variant,
        "building_type": building_type,
        "area_m2": area_m2,
        "rooms": rooms,
        "floors": floors,
        "apartments": apartments,
        "extras": extras,
        "rule_checks": checks,
        "error": None,
    })


@app.get("/projects/{project_id}/parampreview", response_class=HTMLResponse)
def project_param_preview_page(
    request: Request,
    project_id: int,
    variant: str = "komfort",
):
    with SessionFactory() as s:
        project = get_project(s, project_id)
        inp = project.inputs
        try:
            area = float(str(inp.area_m2).replace(",", "."))
        except Exception:
            area = 0.0
        rooms = int(inp.rooms_total or 0)
        floors = int(inp.floors or 1)
        apartments = int(inp.apartments or 1)
        building_type = (inp.building_type or "efh")
        try:
            eur_h = float(str(inp.labor_rate_eur_h).replace(",", "."))
        except Exception:
            eur_h = 72.0
        labor_rate_per_min_cent = int(round((eur_h * 100) / 60.0))
        overhead = inp.overhead_pct or "0"
        profit = inp.profit_pct or "0"
        # latest plan quantities (optional)
        plans = list_plans(s, project_id)
        q = None
        if plans:
            q = compute_plan_quantities(s, plans[0].id)
        extras, checks = preview_param_extras(
            s,
            variant=variant,
            building_type=building_type,
            area_m2=area,
            rooms=rooms,
            floors=floors,
            apartments=apartments,
            labor_rate_per_min_cent=labor_rate_per_min_cent,
            overhead_pct=overhead,
            profit_pct=profit,
            quantities=q,
        )
    return templates.TemplateResponse("param_preview.html", {
        "request": request,
        "variant": variant,
        "building_type": building_type,
        "area_m2": str(inp.area_m2),
        "rooms": rooms,
        "floors": floors,
        "apartments": apartments,
        "extras": extras,
        "rule_checks": checks,
        "error": None,
    })


# ---------------- API (JSON) ----------------
from sqlalchemy import select

@app.get("/api/items/search")
def api_items_search(q: str = ""):
    with SessionFactory() as s:
        items = search_items(s, q, limit=20)
    return [{"id": it.id, "article_no": it.article_no, "name": it.name, "manufacturer": it.manufacturer} for it in items]

@app.post("/api/lv/positions/{position_id}/match")
async def api_lv_set_match(position_id: int, payload: dict):
    item_id = payload.get("item_id")
    if item_id is not None:
        try:
            item_id = int(item_id)
        except Exception:
            return JSONResponse({"error": "item_id must be int or null"}, status_code=400)

    with SessionFactory() as s:
        set_match_manual(s, position_id, item_id)
        from elektrocalc.db.models import LvPosition
        pos = s.execute(select(LvPosition).where(LvPosition.id == position_id)).scalar_one()
        cur = "aktuell: —"
        if pos.match and pos.match.item:
            cur = f"aktuell: {pos.match.item.article_no} – {pos.match.item.name}"
    return JSONResponse({"ok": True, "current": cur})


@app.post("/api/plans/{plan_id}/scale")
async def api_set_scale(plan_id: int, payload: dict):
    scale = payload.get("scale_m_per_px")
    try:
        scale_f = float(scale)
    except Exception:
        return JSONResponse({"error": "scale_m_per_px must be a number (m per px)"}, status_code=400)
    if scale_f <= 0 or scale_f > 1:
        return JSONResponse({"error": "scale_m_per_px out of range"}, status_code=400)
    with SessionFactory() as s:
        set_plan_scale(s, plan_id, str(scale_f))
    return JSONResponse({"ok": True, "scale_m_per_px": str(scale_f)})

@app.post("/api/plans/{plan_id}/rooms")
async def api_add_room(plan_id: int, payload: dict):
    room_type = payload.get("room_type")
    polygon_px = payload.get("polygon_px")
    if not room_type:
        return JSONResponse({"error": "room_type required"}, status_code=400)
    if not isinstance(polygon_px, dict) or "points" not in polygon_px:
        return JSONResponse({"error": "polygon_px must be an object with 'points'"}, status_code=400)
    pts = polygon_px.get("points")
    if not isinstance(pts, list) or len(pts) < 3:
        return JSONResponse({"error": "polygon requires at least 3 points"}, status_code=400)
    clean = []
    for p in pts:
        if not isinstance(p, dict) or "x" not in p or "y" not in p:
            return JSONResponse({"error": "each point must be {x,y}"}, status_code=400)
        try:
            xi = int(p["x"]); yi = int(p["y"])
        except Exception:
            return JSONResponse({"error": "point coordinates must be integers"}, status_code=400)
        if xi < 0 or yi < 0:
            return JSONResponse({"error": "point coordinates must be >= 0"}, status_code=400)
        clean.append({"x": xi, "y": yi})
    name = payload.get("name")
    if name is not None and not isinstance(name, str):
        return JSONResponse({"error": "name must be a string or null"}, status_code=400)
    with SessionFactory() as s:
        r = add_room(s, plan_id, room_type=str(room_type), name=name, polygon_px={"points": clean})
    return JSONResponse({"ok": True, "id": r.id})

@app.post("/api/plans/{plan_id}/points")
async def api_add_point(plan_id: int, payload: dict):
    pt = payload.get("point_type")
    x = payload.get("x_px")
    y = payload.get("y_px")
    if not pt:
        return JSONResponse({"error": "point_type required"}, status_code=400)
    try:
        xi = int(x); yi = int(y)
    except Exception:
        return JSONResponse({"error": "x_px and y_px must be integers"}, status_code=400)
    if xi < 0 or yi < 0:
        return JSONResponse({"error": "x_px/y_px must be >= 0"}, status_code=400)
    attrs = payload.get("attributes") or {}
    if not isinstance(attrs, dict):
        return JSONResponse({"error": "attributes must be an object"}, status_code=400)
    with SessionFactory() as s:
        p = add_point(s, plan_id, point_type=str(pt), x_px=xi, y_px=yi, attributes=attrs)
    return JSONResponse({"ok": True, "id": p.id})
@app.post("/api/plans/{plan_id}/routes")
async def api_add_route(plan_id: int, payload: dict):
    rt = payload.get("route_type") or "CABLE_ROUTE"
    poly = payload.get("polyline_px")
    if not isinstance(poly, dict) or "points" not in poly:
        return JSONResponse({"error":"polyline_px must be object with points"}, status_code=400)
    pts = poly.get("points")
    if not isinstance(pts, list) or len(pts) < 2:
        return JSONResponse({"error":"route requires at least 2 points"}, status_code=400)
    clean=[]
    for p in pts:
        if not isinstance(p, dict) or "x" not in p or "y" not in p:
            return JSONResponse({"error":"each point must be {x,y}"}, status_code=400)
        try:
            xi=int(p["x"]); yi=int(p["y"])
        except Exception:
            return JSONResponse({"error":"x/y must be integers"}, status_code=400)
        if xi < 0 or yi < 0:
            return JSONResponse({"error":"x/y must be >=0"}, status_code=400)
        clean.append({"x": xi, "y": yi})
    attrs = payload.get("attributes") or {}
    if not isinstance(attrs, dict):
        return JSONResponse({"error":"attributes must be object"}, status_code=400)
    with SessionFactory() as s:
        r = add_route(s, plan_id, route_type=str(rt), polyline_px={"points": clean}, attributes=attrs)
    return JSONResponse({"ok": True, "id": r.id})

@app.delete("/api/routes/{route_id}")
async def api_delete_route(route_id: int):
    with SessionFactory() as s:
        delete_route(s, route_id)
    return JSONResponse({"ok": True})

@app.get("/api/plans/{plan_id}/summary")
def api_plan_summary(plan_id: int):
    with SessionFactory() as s:
        summ = compute_plan_summary(s, plan_id)
    return JSONResponse(summ)

@app.get("/api/plans/{plan_id}/quantities")
def api_plan_quantities(plan_id: int):
    with SessionFactory() as s:
        q = compute_plan_quantities(s, plan_id)
    return JSONResponse(q)

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.get("/projects/{project_id}/mapping", response_class=HTMLResponse)
def project_mapping_page(request: Request, project_id: int):
    with SessionFactory() as s:
        project = get_project(s, project_id)
        seed_planmap_if_empty(s, project_id)
        mappings = list_mappings(s, project_id)
    return templates.TemplateResponse("plan_mapping.html", {"request": request, "project": project, "mappings": mappings})


@app.post("/projects/{project_id}/mapping/upsert")
def project_mapping_upsert(
    project_id: int,
    kind: str = Form(...),
    key: str = Form(...),
    variant_key: str = Form(""),
    rate_key: str = Form(...),
    unit: str = Form("St"),
    qty_factor: str = Form("1"),
    description: str = Form(""),
):
    vk = variant_key.strip() or None
    with SessionFactory() as s:
        upsert_mapping(
            s,
            project_id,
            kind=kind.strip(),
            key=key.strip(),
            variant_key=vk,
            rate_key=rate_key.strip(),
            unit=unit.strip(),
            qty_factor=qty_factor.strip(),
            description=(description.strip() or None),
        )
    return RedirectResponse(url=f"/projects/{project_id}/mapping", status_code=303)


@app.post("/projects/{project_id}/mapping/{mapping_id}/delete")
def project_mapping_delete(project_id: int, mapping_id: int):
    with SessionFactory() as s:
        delete_mapping(s, mapping_id)
    return RedirectResponse(url=f"/projects/{project_id}/mapping", status_code=303)



@app.get("/inspection", response_class=HTMLResponse)
def inspection_dashboard(request: Request, error: str | None = None):
    with SessionFactory() as s:
        data = inspection_dashboard_data(s)
    return templates.TemplateResponse("inspection_dashboard.html", {"request": request, "error": error, **data})


@app.post("/inspection/tenants/create")
def inspection_create_tenant(name: str = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_tenant(s, name=name)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/customers/create")
def inspection_create_customer(tenant_id: int = Form(...), name: str = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_customer(s, tenant_id=tenant_id, name=name)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/objects/create")
def inspection_create_object(customer_id: int = Form(...), site_name: str = Form(...), object_name: str = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_object(s, customer_id=customer_id, site_name=site_name, object_name=object_name)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/distributions/create")
def inspection_create_distribution(object_id: int = Form(...), label: str = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_distribution(s, object_id=object_id, label=label)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/orders/create")
def inspection_create_order(object_id: int = Form(...), reason: str = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_order_entry(s, object_id=object_id, reason=reason)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/orders/status")
def inspection_update_order_status(order_id: int = Form(...), new_status: str = Form(...)):
    try:
        with SessionFactory() as s:
            update_inspection_order_status_entry(s, order_id=order_id, new_status=new_status)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/order-distributions/create")
def inspection_assign_order_distribution(order_id: int = Form(...), distribution_id: int = Form(...)):
    try:
        with SessionFactory() as s:
            assign_distribution_to_order_entry(s, order_id=order_id, distribution_id=distribution_id)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/defects/create")
def inspection_create_defect(order_id: int = Form(...), title: str = Form(...), due_date: str | None = Form(None)):
    try:
        with SessionFactory() as s:
            create_inspection_defect(s, order_id=order_id, title=title, due_date=due_date)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/appointments/create")
def inspection_create_appointment(order_id: int = Form(...), starts_at: str = Form(...), ends_at: str | None = Form(None)):
    try:
        with SessionFactory() as s:
            create_inspection_appointment(s, order_id=order_id, starts_at=starts_at, ends_at=ends_at)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/measurement-sets/create")
def inspection_create_measurement_set(order_id: int = Form(...), title: str = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_measurement_set(s, order_id=order_id, title=title)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/measurements/create")
def inspection_create_measurement(
    measurement_set_id: int = Form(...),
    point_label: str = Form(...),
    measured_value: str = Form(...),
    unit: str = Form(...),
):
    try:
        with SessionFactory() as s:
            create_inspection_measurement(
                s,
                measurement_set_id=measurement_set_id,
                point_label=point_label,
                measured_value=measured_value,
                unit=unit,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/reports/create")
def inspection_create_report(order_id: int = Form(...), title: str = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_report(s, order_id=order_id, title=title)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/reports/status")
def inspection_update_report_status(report_id: int = Form(...), new_status: str = Form(...)):
    try:
        with SessionFactory() as s:
            update_inspection_report_status(s, report_id=report_id, new_status=new_status)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/distribution-reports/create")
def inspection_create_distribution_report(
    report_id: int = Form(...),
    distribution_id: int = Form(...),
    summary: str | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_distribution_report(
                s,
                report_id=report_id,
                distribution_id=distribution_id,
                summary=summary,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/tasks/create")
def inspection_create_task(
    tenant_id: int = Form(...),
    title: str = Form(...),
    object_id: int | None = Form(None),
    defect_id: int | None = Form(None),
    report_id: int | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_task(
                s,
                tenant_id=tenant_id,
                title=title,
                object_id=object_id,
                defect_id=defect_id,
                report_id=report_id,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/invoices/create")
def inspection_create_invoice(order_id: int = Form(...), total_cent: int = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_invoice(s, order_id=order_id, total_cent=total_cent)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/invoices/total")
def inspection_update_invoice_total(invoice_id: int = Form(...), total_cent: int = Form(...)):
    try:
        with SessionFactory() as s:
            update_inspection_invoice_total(s, invoice_id=invoice_id, total_cent=total_cent)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/invoices/status")
def inspection_update_invoice_status(invoice_id: int = Form(...), new_status: str = Form(...)):
    try:
        with SessionFactory() as s:
            update_inspection_invoice_status(s, invoice_id=invoice_id, new_status=new_status)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/portal-releases/create")
def inspection_create_portal_release(
    customer_id: int = Form(...),
    release_type: str = Form(...),
    target_id: int = Form(...),
):
    try:
        with SessionFactory() as s:
            create_inspection_portal_release(
                s,
                customer_id=customer_id,
                release_type=release_type,
                target_id=target_id,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/devices/create")
def inspection_create_device(
    tenant_id: int = Form(...),
    name: str = Form(...),
    serial_no: str | None = Form(None),
    calibration_due: str | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_measuring_device(
                s,
                tenant_id=tenant_id,
                name=name,
                serial_no=serial_no,
                calibration_due=calibration_due,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/documents/create")
def inspection_create_document_record(
    tenant_id: int = Form(...),
    file_name: str = Form(...),
    category: str = Form("general"),
    visibility: str = Form("internal"),
    object_id: int | None = Form(None),
    inspection_order_id: int | None = Form(None),
    defect_id: int | None = Form(None),
    report_id: int | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_document_record(
                s,
                tenant_id=tenant_id,
                file_name=file_name,
                category=category,
                visibility=visibility,
                object_id=object_id,
                inspection_order_id=inspection_order_id,
                defect_id=defect_id,
                report_id=report_id,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/communication/create")
def inspection_create_communication(
    tenant_id: int = Form(...),
    message: str = Form(...),
    direction: str = Form("internal"),
    task_id: int | None = Form(None),
    customer_id: int | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_communication_entry(
                s,
                tenant_id=tenant_id,
                message=message,
                direction=direction,
                task_id=task_id,
                customer_id=customer_id,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/defect-deadlines/create")
def inspection_create_defect_deadline(defect_id: int = Form(...), due_date: str = Form(...), note: str | None = Form(None)):
    try:
        with SessionFactory() as s:
            create_inspection_defect_deadline(s, defect_id=defect_id, due_date=due_date, note=note)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/approval-steps/create")
def inspection_create_approval_step(
    tenant_id: int = Form(...),
    target_type: str = Form(...),
    target_id: int = Form(...),
    required_role: str = Form(...),
):
    try:
        with SessionFactory() as s:
            create_inspection_approval_step(
                s,
                tenant_id=tenant_id,
                target_type=target_type,
                target_id=target_id,
                required_role=required_role,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/approval-steps/status")
def inspection_update_approval_step_status(step_id: int = Form(...), new_status: str = Form(...)):
    try:
        with SessionFactory() as s:
            update_inspection_approval_step_status(s, step_id=step_id, new_status=new_status)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/notifications/create")
def inspection_create_notification(
    tenant_id: int = Form(...),
    title: str = Form(...),
    message: str = Form(...),
    related_type: str | None = Form(None),
    related_id: int | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_notification(
                s,
                tenant_id=tenant_id,
                title=title,
                message=message,
                related_type=related_type,
                related_id=related_id,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/cycles/create")
def inspection_create_cycle(object_id: int = Form(...), interval_months: int = Form(...), next_due_date: str = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_cycle_entry(
                s,
                object_id=object_id,
                interval_months=interval_months,
                next_due_date=next_due_date,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/backups/create")
def inspection_create_backup_run(
    tenant_id: int = Form(...),
    status: str = Form("ok"),
    location: str | None = Form(None),
    finished_at: str | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_backup_run(
                s,
                tenant_id=tenant_id,
                status=status,
                location=location,
                finished_at=finished_at,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/thermography/create")
def inspection_create_thermography(
    object_id: int = Form(...),
    defect_id: int | None = Form(None),
    image_ref: str = Form(...),
    max_temp_c: str | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_thermography_entry(
                s,
                object_id=object_id,
                defect_id=defect_id,
                image_ref=image_ref,
                max_temp_c=max_temp_c,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/calibrations/create")
def inspection_create_calibration(
    device_id: int = Form(...),
    calibrated_at: str = Form(...),
    valid_until: str = Form(...),
    certificate_ref: str | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_device_calibration(
                s,
                device_id=device_id,
                calibrated_at=calibrated_at,
                valid_until=valid_until,
                certificate_ref=certificate_ref,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/number-sequences/create")
def inspection_create_number_sequence(tenant_id: int = Form(...), scope: str = Form(...), prefix: str = Form("")):
    try:
        with SessionFactory() as s:
            create_inspection_number_sequence(s, tenant_id=tenant_id, scope=scope, prefix=prefix)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/number-sequences/issue")
def inspection_issue_number(sequence_id: int = Form(...)):
    try:
        with SessionFactory() as s:
            issued = issue_inspection_number(s, sequence_id=sequence_id)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url=f"/inspection?error={urllib.parse.quote('Nummer vergeben: ' + issued)}", status_code=303)


@app.post("/inspection/payments/create")
def inspection_create_payment(invoice_id: int = Form(...), amount_cent: int = Form(...)):
    try:
        with SessionFactory() as s:
            create_inspection_payment_entry(s, invoice_id=invoice_id, amount_cent=amount_cent)
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/retention-rules/create")
def inspection_create_retention_rule(
    tenant_id: int = Form(...),
    data_type: str = Form(...),
    retention_days: int = Form(...),
    delete_mode: str = Form("archive"),
):
    try:
        with SessionFactory() as s:
            create_inspection_retention_rule(
                s,
                tenant_id=tenant_id,
                data_type=data_type,
                retention_days=retention_days,
                delete_mode=delete_mode,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)


@app.post("/inspection/restore-tests/create")
def inspection_create_restore_test(
    tenant_id: int = Form(...),
    backup_run_id: int | None = Form(None),
    status: str = Form("passed"),
    notes: str | None = Form(None),
):
    try:
        with SessionFactory() as s:
            create_inspection_restore_test(
                s,
                tenant_id=tenant_id,
                backup_run_id=backup_run_id,
                status=status,
                notes=notes,
            )
    except ValueError as exc:
        return RedirectResponse(url=f"/inspection?error={urllib.parse.quote(str(exc))}", status_code=303)
    return RedirectResponse(url="/inspection", status_code=303)
