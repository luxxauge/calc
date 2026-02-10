# Changelog

## v2.6.0 (2026-02-09)
### Added
- LV-Kalk: Plan-Auswahl per Dropdown (statt Plan-ID manuell)
- Plan→Extras anwenden optional auf alle Varianten (Checkbox)
### Fixed
- Validierung: Plan muss zum Projekt gehören (sonst 400)



## v2.5.0 (2026-02-09)
### Added
- Plan→Kalk Mapping pro Projekt (Route-/Punkt-Typ → Rate-Key/Unit/Faktor, optional pro Variante)
- WebUI: Mapping-Seite `/projects/{project_id}/mapping`
- LV: Plan→Extras anwenden (`POST /lv/{doc_id}/calc/apply_plan`) erstellt CalcExtraLines aus Plan-Quantities
- Plan Quantities Export: `/plans/{plan_id}/quantities.xlsx` und `/plans/{plan_id}/quantities.pdf`



## v2.4.1 (2026-02-09)
### Fixed
- Plan-Editor 500 behoben: fehlender Import von list_routes/add_route/delete_route
- favicon.ico: keine 404 mehr

## v2.4.0 (2026-01-30)
### Added
- Raumflächenberechnung (px² + m² bei gesetztem Maßstab) via Shoelace
- Plan-Quantities: Routenlängen nach Typ (px/m) + Punktcounts
- API: `/api/plans/{plan_id}/quantities`
- Projekt-Param-Preview nutzt automatisch Quantities aus dem neuesten Plan (optional) und stellt sie ParamRules als Variablen zur Verfügung (`quantities__...`).


## v2.3.0 (2026-01-30)
### Added
- Grundriss/Plan-Editor: Leitungswege (Polyline) als PlanRoute inkl. Canvas-Tool
- API: Routen anlegen/löschen + Plan-Summary (Counts/Längen)
- Plan-Editor: Summary-Block (Räume/Punkte/Routen + Route total in m wenn Maßstab gesetzt)


## v2.2.0 (2026-01-30)
### Added
- Projektgebundener Param-Preview: `/projects/{project_id}/parampreview` (nutzt Projektinputs inkl. Lohnsatz/OH/Profit)
- Kalkulationsparameter in Projektinputs: Lohnsatz €/h, Overhead, Profit
- LV: Button/Endpoint "Alle Varianten rechnen" (`/lv/{doc_id}/calc/run_all`) + Redirect zum Variantenvergleich

### Fixed
- Alembic Migration ergänzt für neue Projektinput-Felder


## v2.1.0 (2026-01-30)
### Added
- Variantenvergleich (LV) als „fertige“ Ansicht inkl. Export:
  - Excel Export: `/lv/{doc_id}/compare.xlsx`
  - PDF Export: `/lv/{doc_id}/compare.pdf`
- Compare-Daten als zentraler Builder `_build_lv_compare_data(...)` für UI + Exporte.
- UI-Buttons für Export (Excel/PDF) in `lv_compare.html`.
- Link „Variantenvergleich“ in der LV-Detailseite (`lv_doc.html`).

### Fixed
- Fehlende Imports in `web/app.py` (RateCard + ParamRules Services), die zu `NameError` führen konnten.
- `requirements.txt` um `reportlab` ergänzt (PDF Export).

### Notes
- Exporte enthalten Summary, Delta-Tabelle (inkl. EXTRAS-Zeile) und Extras-Breakdown.

## v2.0.1
- Robustheitsfixes + Migration/SQLite-Kompatibilität (Unique-Constraints via unique indexes, Date-Import, cat_item→item, etc.)
- Preview (`/parampreview`) + Basis-Variantenvergleich (LV) + Debug-Checks

## v1.9.1
- ParamRules Validierung (Expr/RateKey) + `safe_eval` hardening + RateCard Delete + kleine Robustheitsfixes

## v1.0 – v1.9
- Schema, WebUI, LV parallel, Kalkulation, Rules, Traceability, Varianten, Parametrik, RateCard, ParamRules
