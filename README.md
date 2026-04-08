# ElektroCalc – Vollständige Offline Web-UI (FastAPI) – v1

**Ziel:** 100% offline (localhost), inkl. **Grundriss-PDF/JPG/PNG Import**, **PDF-Rendering (PyMuPDF)**,
**Plan-Editor (Canvas)** für **Maßstab**, **Räume (Polygone)** und **Punkte (Marker)**, plus Schema v1 + Alembic.

## Start (Dev)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
python launcher.py
```

Öffnet automatisch: http://127.0.0.1:8765

## Enthalten
- Projects / Inputs
- Plans: Upload + PDF→PNG Rendercache (preview/work)
- Plan Editor:
  - Maßstab setzen (2-Punkt)
  - Räume zeichnen (Polygon + room_type + name)
  - Punkte setzen (point_type, z.B. SOCKET/DATA/LIGHT_OUTLET/SWITCH_POINT/UV)
- DB: Schema v1 (CalcRuns/Compliance etc. vorhanden)
- Calc Runs: aktuell "minimal" (Snapshot erzeugen; die echte Kalkulationsengine folgt als nächster Schritt)

## Offline Hinweis
Keine externen CDNs. Alles lokal.


### Notes
- `alembic.ini` uses `sqlite:///data/electrocalc.db` to match the app settings.


## Artikel-Katalog Import (xlsx)
- UI: /catalog
- Upload → Mapping → Import (Upsert) + Price history


## LV / Ausschreibung (xlsx/csv/txt)
- Pro Projekt mehrere LVs möglich
- UI: /projects/<id>/lv
- Import: xlsx/csv mit Mapping, txt als Zeilenimport (optional posno;qty;unit;text;longtext)
- Zuordnung: /lv/<doc_id>/match (Suche im Artikel-Katalog + manuelles Setzen)


## Zeitkatalog (v1.4)
- UI: /labor
- Tätigkeiten: Code, Einheit, Minuten/Einheit
- Regeln: Pattern (Substring/Regex) + Priorität → Tätigkeit
- Kalkulation nutzt Regeln bevorzugt, fällt sonst auf Heuristik zurück.


## Kalkulation – Traceability (v1.5)
- calc_detail zeigt Quelle (rule/heuristic) + Task-Code + Regelinfo.


## Variantenpakete (DIN 18015) (v1.6)
- UI: /variants
- Profile: standard/komfort/premium
- Regeln: match über Task-Code (Zeitkatalog) oder Pattern (LV-Text), mit Prio
- Wirkung: Multiplikatoren auf Material/Lohn + optionale Zusatzminuten

## Variantenvergleich (v1.6)
- UI: /lv/<doc_id>/compare
- Vergleicht jeweils den neuesten Kalkulationslauf je Variante.


## Parametrische Zusatzpositionen (v1.7)
- Inputs: Gebäudetyp (EFH/MFH/Gewerbe), Wohneinheiten (MFH), Fläche, Zimmer.
- Komfort/Premium generieren Zusatzpositionen (z.B. Steckdosen-/Datendosen-Dichte) als `calc_extra_line`.
- UI: in Calc Detail sichtbar; Summen/Compare berücksichtigen Extras.


## Rate Card (v1.8)
- UI: /ratecard
- Pflegt Unit-Materialpreise und optional Item-Mapping (Item-ID) für parametrische Zusatzpositionen.
- Wenn Item-ID gesetzt ist, zieht die Kalkulation den latest VK aus ItemPrice.


## Parametrische Regeln (v1.9)
- UI: /paramrules
- Menge über sicheren Ausdruck (keine Codeausführung).
- Generator nutzt Rate-Card Key → Unitpreis/Task/Item-Mapping.


## Generator Preview (v2.0)
- UI: /parampreview
- Simuliert Zusatzpositionen aus ParamRules/RateCard, inkl. Rule-Check und Fehlerhinweisen.
- Variantenvergleich enthält eine synthetische 'EXTRAS' Zeile für Zusatzpositionen.


## v2.1 – Variantenvergleich Export
- CSV Export des Variantenvergleichs (/lv/{doc_id}/compare.csv)
- PDF Export vorbereitet (Platzhalter)

## Mandantenfähige Prüfsoftware (MVP-1 Fundament)
- UI: `/inspection`
- Enthält den objektzentrierten Kernfluss aus dem Lastenheft: Mandant -> Kunde -> Standort/Objekt -> Verteilung -> Prüfauftrag -> Mangel/Bericht.
- Prüfaufträge können Verteilungen explizit zugeordnet werden (Tabelle `insp_inspection_order_distribution`) für Hauptbericht/Teilbericht-Logik.
- Neue Datenbasis inkl. Mandantentrennung in Tabellenpräfix `insp_` (Alembic Revisionen `0012inspectionmvp`, `0013inspectionorderdist`).
- Zusätzlich umgesetzt (nächste Module): Termin-/Einsatzplanung, Messprotokoll-Engine (Messsatz/Messwert), Aufgabenmodul sowie Portal-Freigaben mit Formularen in `/inspection`.
- Logische Verknüpfungen: Teilbericht je Verteilung nur bei passender Prüfauftrag-Verteilungszuordnung; Portalfreigaben prüfen Kundenbezug des Zielobjekts (z.B. Bericht/Mangel/Objekt).
- Kaufmännischer Einstieg: Rechnungsanlage, Statusfluss und Änderungsstopp des Betrags nach Finalisierung.
- Weitere Module: Geräteverwaltung, DMS-Dokumentbezug, Kommunikationslogik und Audit-Log mit Erfassungsformularen im Inspection-Dashboard.
- Freigabe-/Finalisierungslogik erweitert: Status-Workflows für Prüfauftrag und Bericht; Messwerte/Teilberichte werden nach Finalisierung gesperrt.
- Nächste 5 Blöcke umgesetzt: Mängelfristen, Freigabeschritte, Benachrichtigungen, Prüfzyklen und Backup-Run-Logging.
