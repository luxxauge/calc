from __future__ import annotations

from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from elektrocalc.db.models import (
    InspTenant,
    InspCustomer,
    InspSite,
    InspObject,
    InspDistribution,
    InspInspectionOrder,
    InspInspectionOrderDistribution,
    InspAppointment,
    InspMeasurementSet,
    InspMeasurement,
    InspDefect,
    InspReport,
    InspDistributionReport,
    InspTask,
    InspInvoice,
    InspPortalRelease,
    InspMeasuringDevice,
    InspDocument,
    InspCommunicationEntry,
    InspAuditLog,
    InspDefectDeadline,
    InspApprovalStep,
    InspNotification,
    InspInspectionCycle,
    InspBackupRun,
)


def list_tenants(session: Session) -> list[InspTenant]:
    return list(session.execute(select(InspTenant).order_by(InspTenant.name)).scalars().all())


def create_tenant(session: Session, name: str) -> InspTenant:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Mandantenname darf nicht leer sein")
    tenant = InspTenant(name=clean_name)
    session.add(tenant)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("Mandant existiert bereits") from exc
    session.refresh(tenant)
    return tenant


def create_customer(session: Session, tenant_id: int, name: str) -> InspCustomer:
    tenant = session.get(InspTenant, tenant_id)
    if tenant is None:
        raise ValueError("Mandant nicht gefunden")
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Kundenname darf nicht leer sein")
    customer = InspCustomer(tenant_id=tenant_id, name=clean_name)
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


def create_object(session: Session, customer_id: int, site_name: str, object_name: str) -> InspObject:
    customer = session.get(InspCustomer, customer_id)
    if customer is None:
        raise ValueError("Kunde nicht gefunden")
    clean_site_name = site_name.strip()
    clean_object_name = object_name.strip()
    if not clean_site_name or not clean_object_name:
        raise ValueError("Standort und Objektname sind Pflicht")
    site = session.execute(
        select(InspSite).where(
            InspSite.customer_id == customer_id,
            InspSite.name == clean_site_name,
        )
    ).scalar_one_or_none()
    if site is None:
        site = InspSite(tenant_id=customer.tenant_id, customer_id=customer_id, name=clean_site_name)
        session.add(site)
        session.flush()
    obj = InspObject(tenant_id=customer.tenant_id, customer_id=customer_id, site_id=site.id, name=clean_object_name)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def add_distribution(session: Session, object_id: int, label: str) -> InspDistribution:
    obj = session.get(InspObject, object_id)
    if obj is None:
        raise ValueError("Objekt nicht gefunden")
    distribution = InspDistribution(
        tenant_id=obj.tenant_id,
        object_id=object_id,
        label=label.strip(),
    )
    session.add(distribution)
    session.commit()
    session.refresh(distribution)
    return distribution


def create_inspection_order(session: Session, object_id: int, reason: str) -> InspInspectionOrder:
    obj = session.get(InspObject, object_id)
    if obj is None:
        raise ValueError("Objekt nicht gefunden")
    order = InspInspectionOrder(
        tenant_id=obj.tenant_id,
        object_id=object_id,
        reason=reason.strip(),
        status="planned",
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def update_inspection_order_status(session: Session, order_id: int, new_status: str) -> InspInspectionOrder:
    order = session.get(InspInspectionOrder, order_id)
    if order is None:
        raise ValueError("Prüfauftrag nicht gefunden")
    next_status = new_status.strip().lower()
    allowed_next = {
        "draft": {"planned", "archived"},
        "planned": {"in_progress", "archived"},
        "in_progress": {"technical_done", "archived"},
        "technical_done": {"finalized", "archived"},
        "finalized": {"archived"},
        "archived": set(),
    }
    if next_status not in allowed_next.get(order.status, set()):
        raise ValueError(f"Statuswechsel {order.status} -> {next_status} ist nicht erlaubt")
    order.status = next_status
    session.commit()
    session.refresh(order)
    return order


def assign_distribution_to_order(session: Session, order_id: int, distribution_id: int) -> InspInspectionOrderDistribution:
    order = session.get(InspInspectionOrder, order_id)
    if order is None:
        raise ValueError("Prüfauftrag nicht gefunden")
    distribution = session.get(InspDistribution, distribution_id)
    if distribution is None:
        raise ValueError("Verteilung nicht gefunden")
    if distribution.object_id != order.object_id:
        raise ValueError("Verteilung gehört nicht zum Objekt des Prüfauftrags")
    existing = session.execute(
        select(InspInspectionOrderDistribution).where(
            InspInspectionOrderDistribution.inspection_order_id == order_id,
            InspInspectionOrderDistribution.distribution_id == distribution_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    link = InspInspectionOrderDistribution(
        tenant_id=order.tenant_id,
        inspection_order_id=order_id,
        distribution_id=distribution_id,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def create_defect(session: Session, order_id: int, title: str, due_date: str | None) -> InspDefect:
    order = session.get(InspInspectionOrder, order_id)
    if order is None:
        raise ValueError("Prüfauftrag nicht gefunden")
    defect = InspDefect(
        tenant_id=order.tenant_id,
        inspection_order_id=order.id,
        object_id=order.object_id,
        title=title.strip(),
        status="open",
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None,
    )
    session.add(defect)
    session.commit()
    session.refresh(defect)
    return defect


def create_appointment(
    session: Session,
    order_id: int,
    starts_at: str,
    ends_at: str | None,
) -> InspAppointment:
    order = session.get(InspInspectionOrder, order_id)
    if order is None:
        raise ValueError("Prüfauftrag nicht gefunden")
    start_ts = datetime.fromisoformat(starts_at.strip())
    end_ts = datetime.fromisoformat(ends_at.strip()) if ends_at else None
    if end_ts and end_ts < start_ts:
        raise ValueError("Terminende liegt vor dem Start")
    appointment = InspAppointment(
        tenant_id=order.tenant_id,
        inspection_order_id=order.id,
        starts_at=start_ts,
        ends_at=end_ts,
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment


def create_measurement_set(session: Session, order_id: int, title: str) -> InspMeasurementSet:
    order = session.get(InspInspectionOrder, order_id)
    if order is None:
        raise ValueError("Prüfauftrag nicht gefunden")
    measurement_set = InspMeasurementSet(
        tenant_id=order.tenant_id,
        inspection_order_id=order.id,
        title=title.strip(),
    )
    session.add(measurement_set)
    session.commit()
    session.refresh(measurement_set)
    return measurement_set


def create_measurement(
    session: Session,
    measurement_set_id: int,
    point_label: str,
    measured_value: str,
    unit: str,
) -> InspMeasurement:
    measurement_set = session.get(InspMeasurementSet, measurement_set_id)
    if measurement_set is None:
        raise ValueError("Messsatz nicht gefunden")
    order = session.get(InspInspectionOrder, measurement_set.inspection_order_id)
    if order and order.status == "finalized":
        raise ValueError("Messwerte dürfen bei finalisiertem Prüfauftrag nicht mehr ergänzt werden")
    measurement = InspMeasurement(
        tenant_id=measurement_set.tenant_id,
        measurement_set_id=measurement_set.id,
        point_label=point_label.strip(),
        measured_value=measured_value.strip(),
        unit=unit.strip(),
    )
    session.add(measurement)
    session.commit()
    session.refresh(measurement)
    return measurement


def create_report(session: Session, order_id: int, title: str) -> InspReport:
    order = session.get(InspInspectionOrder, order_id)
    if order is None:
        raise ValueError("Prüfauftrag nicht gefunden")
    report = InspReport(
        tenant_id=order.tenant_id,
        inspection_order_id=order.id,
        title=title.strip(),
        status="draft",
    )
    session.add(report)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("Für diesen Prüfauftrag existiert bereits ein Hauptbericht") from exc
    session.refresh(report)
    return report


def update_report_status(session: Session, report_id: int, new_status: str) -> InspReport:
    report = session.get(InspReport, report_id)
    if report is None:
        raise ValueError("Bericht nicht gefunden")
    next_status = new_status.strip().lower()
    allowed_next = {
        "draft": {"for_approval", "archived"},
        "for_approval": {"approved", "draft", "archived"},
        "approved": {"finalized", "archived"},
        "finalized": {"published", "archived"},
        "published": {"archived"},
        "archived": set(),
    }
    if next_status not in allowed_next.get(report.status, set()):
        raise ValueError(f"Statuswechsel {report.status} -> {next_status} ist nicht erlaubt")
    report.status = next_status
    session.commit()
    session.refresh(report)
    return report


def create_distribution_report(
    session: Session,
    report_id: int,
    distribution_id: int,
    summary: str | None,
) -> InspDistributionReport:
    report = session.get(InspReport, report_id)
    if report is None:
        raise ValueError("Bericht nicht gefunden")
    distribution = session.get(InspDistribution, distribution_id)
    if distribution is None:
        raise ValueError("Verteilung nicht gefunden")
    order = session.get(InspInspectionOrder, report.inspection_order_id)
    if order is None:
        raise ValueError("Prüfauftrag nicht gefunden")
    if distribution.object_id != order.object_id:
        raise ValueError("Verteilung passt nicht zum Objekt des Berichts")
    link = session.execute(
        select(InspInspectionOrderDistribution).where(
            InspInspectionOrderDistribution.inspection_order_id == order.id,
            InspInspectionOrderDistribution.distribution_id == distribution.id,
        )
    ).scalar_one_or_none()
    if link is None:
        raise ValueError("Verteilung ist dem Prüfauftrag nicht zugeordnet")
    if report.status in {"finalized", "published", "archived"}:
        raise ValueError("Teilberichte dürfen nach Finalisierung nicht mehr angelegt werden")
    dist_report = InspDistributionReport(
        tenant_id=report.tenant_id,
        report_id=report.id,
        distribution_id=distribution.id,
        summary=(summary or "").strip() or None,
    )
    session.add(dist_report)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("Teilbericht für diese Verteilung existiert bereits") from exc
    session.refresh(dist_report)
    return dist_report


def create_task(
    session: Session,
    tenant_id: int,
    title: str,
    object_id: int | None,
    defect_id: int | None,
    report_id: int | None,
) -> InspTask:
    tenant = session.get(InspTenant, tenant_id)
    if tenant is None:
        raise ValueError("Mandant nicht gefunden")
    obj = session.get(InspObject, object_id) if object_id else None
    defect = session.get(InspDefect, defect_id) if defect_id else None
    report = session.get(InspReport, report_id) if report_id else None
    if obj is not None and obj.tenant_id != tenant_id:
        raise ValueError("Objekt gehört nicht zum Mandanten")
    if defect is not None and defect.tenant_id != tenant_id:
        raise ValueError("Mangel gehört nicht zum Mandanten")
    if report is not None and report.tenant_id != tenant_id:
        raise ValueError("Bericht gehört nicht zum Mandanten")
    if obj is not None and defect is not None and defect.object_id != obj.id:
        raise ValueError("Mangel passt nicht zum Objekt")
    task = InspTask(
        tenant_id=tenant_id,
        object_id=object_id,
        defect_id=defect_id,
        report_id=report_id,
        title=title.strip(),
        status="open",
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def create_portal_release(
    session: Session,
    customer_id: int,
    release_type: str,
    target_id: int,
) -> InspPortalRelease:
    customer = session.get(InspCustomer, customer_id)
    if customer is None:
        raise ValueError("Kunde nicht gefunden")
    release_type_clean = release_type.strip().lower()
    if release_type_clean not in {"report", "defect", "object", "document"}:
        raise ValueError("release_type muss report|defect|object|document sein")
    if release_type_clean == "report":
        report = session.get(InspReport, target_id)
        if report is None:
            raise ValueError("Bericht-Ziel nicht gefunden")
        order = session.get(InspInspectionOrder, report.inspection_order_id)
        obj = session.get(InspObject, order.object_id) if order else None
        if obj is None or obj.customer_id != customer.id:
            raise ValueError("Bericht gehört nicht zum Kunden")
    if release_type_clean == "defect":
        defect = session.get(InspDefect, target_id)
        if defect is None:
            raise ValueError("Mangel-Ziel nicht gefunden")
        obj = session.get(InspObject, defect.object_id)
        if obj is None or obj.customer_id != customer.id:
            raise ValueError("Mangel gehört nicht zum Kunden")
    if release_type_clean == "object":
        obj = session.get(InspObject, target_id)
        if obj is None or obj.customer_id != customer.id:
            raise ValueError("Objekt gehört nicht zum Kunden")
    portal_release = InspPortalRelease(
        tenant_id=customer.tenant_id,
        customer_id=customer.id,
        release_type=release_type_clean,
        target_id=target_id,
    )
    session.add(portal_release)
    session.commit()
    session.refresh(portal_release)
    return portal_release


def create_invoice(session: Session, order_id: int, total_cent: int) -> InspInvoice:
    order = session.get(InspInspectionOrder, order_id)
    if order is None:
        raise ValueError("Prüfauftrag nicht gefunden")
    invoice = InspInvoice(
        tenant_id=order.tenant_id,
        inspection_order_id=order.id,
        status="draft",
        total_cent=max(0, int(total_cent)),
    )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    log_audit(session, order.tenant_id, "invoice_created", "invoice", invoice.id)
    return invoice


def update_invoice_total(session: Session, invoice_id: int, total_cent: int) -> InspInvoice:
    invoice = session.get(InspInvoice, invoice_id)
    if invoice is None:
        raise ValueError("Rechnung nicht gefunden")
    if invoice.status not in {"draft", "freigegeben"}:
        raise ValueError("Betrag darf nach Finalisierung nicht mehr geändert werden")
    invoice.total_cent = max(0, int(total_cent))
    session.commit()
    session.refresh(invoice)
    return invoice


def update_invoice_status(session: Session, invoice_id: int, new_status: str) -> InspInvoice:
    invoice = session.get(InspInvoice, invoice_id)
    if invoice is None:
        raise ValueError("Rechnung nicht gefunden")
    next_status = new_status.strip().lower()
    allowed_next = {
        "draft": {"freigegeben", "storniert"},
        "freigegeben": {"finalisiert", "storniert"},
        "finalisiert": {"versendet", "korrigiert", "storniert"},
        "versendet": {"bezahlt", "storniert", "korrigiert"},
        "bezahlt": {"archiviert"},
        "storniert": {"archiviert"},
        "korrigiert": {"archiviert"},
        "archiviert": set(),
    }
    if next_status not in allowed_next.get(invoice.status, set()):
        raise ValueError(f"Statuswechsel {invoice.status} -> {next_status} ist nicht erlaubt")
    invoice.status = next_status
    session.commit()
    session.refresh(invoice)
    log_audit(session, invoice.tenant_id, "invoice_status_changed", "invoice", invoice.id)
    return invoice


def create_measuring_device(
    session: Session,
    tenant_id: int,
    name: str,
    serial_no: str | None,
    calibration_due: str | None,
) -> InspMeasuringDevice:
    if session.get(InspTenant, tenant_id) is None:
        raise ValueError("Mandant nicht gefunden")
    device = InspMeasuringDevice(
        tenant_id=tenant_id,
        name=name.strip(),
        serial_no=(serial_no or "").strip() or None,
        calibration_due=datetime.strptime(calibration_due, "%Y-%m-%d").date() if calibration_due else None,
        status="active",
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    log_audit(session, tenant_id, "device_created", "measuring_device", device.id)
    return device


def create_document_record(
    session: Session,
    tenant_id: int,
    file_name: str,
    category: str,
    visibility: str,
    object_id: int | None,
    inspection_order_id: int | None,
    defect_id: int | None,
    report_id: int | None,
) -> InspDocument:
    if session.get(InspTenant, tenant_id) is None:
        raise ValueError("Mandant nicht gefunden")
    if not any([object_id, inspection_order_id, defect_id, report_id]):
        raise ValueError("Dokument braucht mindestens einen Fachbezug")
    doc = InspDocument(
        tenant_id=tenant_id,
        file_name=file_name.strip(),
        category=category.strip() or "general",
        visibility=visibility.strip() or "internal",
        object_id=object_id,
        inspection_order_id=inspection_order_id,
        defect_id=defect_id,
        report_id=report_id,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    log_audit(session, tenant_id, "document_record_created", "document", doc.id)
    return doc


def create_communication_entry(
    session: Session,
    tenant_id: int,
    message: str,
    direction: str,
    task_id: int | None,
    customer_id: int | None,
) -> InspCommunicationEntry:
    if session.get(InspTenant, tenant_id) is None:
        raise ValueError("Mandant nicht gefunden")
    if task_id and session.get(InspTask, task_id) is None:
        raise ValueError("Aufgabe nicht gefunden")
    if customer_id and session.get(InspCustomer, customer_id) is None:
        raise ValueError("Kunde nicht gefunden")
    entry = InspCommunicationEntry(
        tenant_id=tenant_id,
        message=message.strip(),
        direction=direction.strip().lower() or "internal",
        task_id=task_id,
        customer_id=customer_id,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    log_audit(session, tenant_id, "communication_entry_created", "communication_entry", entry.id)
    return entry


def log_audit(
    session: Session,
    tenant_id: int,
    action: str,
    entity_type: str,
    entity_id: int | None,
    actor: str | None = None,
) -> InspAuditLog:
    audit = InspAuditLog(
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)
    return audit


def create_defect_deadline(session: Session, defect_id: int, due_date: str, note: str | None) -> InspDefectDeadline:
    defect = session.get(InspDefect, defect_id)
    if defect is None:
        raise ValueError("Mangel nicht gefunden")
    deadline = InspDefectDeadline(
        tenant_id=defect.tenant_id,
        defect_id=defect.id,
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date(),
        note=(note or "").strip() or None,
    )
    session.add(deadline)
    session.commit()
    session.refresh(deadline)
    return deadline


def create_approval_step(
    session: Session,
    tenant_id: int,
    target_type: str,
    target_id: int,
    required_role: str,
) -> InspApprovalStep:
    if session.get(InspTenant, tenant_id) is None:
        raise ValueError("Mandant nicht gefunden")
    step = InspApprovalStep(
        tenant_id=tenant_id,
        target_type=target_type.strip().lower(),
        target_id=target_id,
        required_role=required_role.strip().lower(),
        status="pending",
    )
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def update_approval_step_status(session: Session, step_id: int, new_status: str) -> InspApprovalStep:
    step = session.get(InspApprovalStep, step_id)
    if step is None:
        raise ValueError("Freigabeschritt nicht gefunden")
    status = new_status.strip().lower()
    if status not in {"pending", "approved", "rejected"}:
        raise ValueError("Status muss pending|approved|rejected sein")
    step.status = status
    step.decided_at = datetime.utcnow() if status in {"approved", "rejected"} else None
    session.commit()
    session.refresh(step)
    return step


def create_notification(
    session: Session,
    tenant_id: int,
    title: str,
    message: str,
    related_type: str | None,
    related_id: int | None,
) -> InspNotification:
    if session.get(InspTenant, tenant_id) is None:
        raise ValueError("Mandant nicht gefunden")
    notification = InspNotification(
        tenant_id=tenant_id,
        title=title.strip(),
        message=message.strip(),
        related_type=(related_type or "").strip() or None,
        related_id=related_id,
        status="open",
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def create_inspection_cycle(
    session: Session,
    object_id: int,
    interval_months: int,
    next_due_date: str,
) -> InspInspectionCycle:
    obj = session.get(InspObject, object_id)
    if obj is None:
        raise ValueError("Objekt nicht gefunden")
    cycle = InspInspectionCycle(
        tenant_id=obj.tenant_id,
        object_id=obj.id,
        interval_months=max(1, int(interval_months)),
        next_due_date=datetime.strptime(next_due_date, "%Y-%m-%d").date(),
        status="active",
    )
    session.add(cycle)
    session.commit()
    session.refresh(cycle)
    return cycle


def create_backup_run(
    session: Session,
    tenant_id: int,
    status: str,
    location: str | None,
    finished_at: str | None,
) -> InspBackupRun:
    if session.get(InspTenant, tenant_id) is None:
        raise ValueError("Mandant nicht gefunden")
    backup = InspBackupRun(
        tenant_id=tenant_id,
        status=status.strip().lower() or "ok",
        location=(location or "").strip() or None,
        finished_at=datetime.fromisoformat(finished_at.strip()) if finished_at else None,
    )
    session.add(backup)
    session.commit()
    session.refresh(backup)
    return backup


def inspection_dashboard_data(session: Session) -> dict[str, list]:
    order_distribution_links = list(
        session.execute(
            select(InspInspectionOrderDistribution).order_by(InspInspectionOrderDistribution.id.desc()).limit(100)
        ).scalars().all()
    )
    return {
        "tenants": list_tenants(session),
        "customers": list(session.execute(select(InspCustomer).order_by(InspCustomer.id.desc()).limit(30)).scalars().all()),
        "objects": list(session.execute(select(InspObject).order_by(InspObject.id.desc()).limit(30)).scalars().all()),
        "orders": list(session.execute(select(InspInspectionOrder).order_by(InspInspectionOrder.id.desc()).limit(30)).scalars().all()),
        "defects": list(session.execute(select(InspDefect).order_by(InspDefect.id.desc()).limit(30)).scalars().all()),
        "reports": list(session.execute(select(InspReport).order_by(InspReport.id.desc()).limit(30)).scalars().all()),
        "distribution_reports": list(session.execute(select(InspDistributionReport).order_by(InspDistributionReport.id.desc()).limit(30)).scalars().all()),
        "distributions": list(session.execute(select(InspDistribution).order_by(InspDistribution.id.desc()).limit(30)).scalars().all()),
        "order_distribution_links": order_distribution_links,
        "appointments": list(session.execute(select(InspAppointment).order_by(InspAppointment.id.desc()).limit(30)).scalars().all()),
        "measurement_sets": list(session.execute(select(InspMeasurementSet).order_by(InspMeasurementSet.id.desc()).limit(30)).scalars().all()),
        "measurements": list(session.execute(select(InspMeasurement).order_by(InspMeasurement.id.desc()).limit(30)).scalars().all()),
        "tasks": list(session.execute(select(InspTask).order_by(InspTask.id.desc()).limit(30)).scalars().all()),
        "invoices": list(session.execute(select(InspInvoice).order_by(InspInvoice.id.desc()).limit(30)).scalars().all()),
        "portal_releases": list(session.execute(select(InspPortalRelease).order_by(InspPortalRelease.id.desc()).limit(30)).scalars().all()),
        "measuring_devices": list(session.execute(select(InspMeasuringDevice).order_by(InspMeasuringDevice.id.desc()).limit(30)).scalars().all()),
        "documents": list(session.execute(select(InspDocument).order_by(InspDocument.id.desc()).limit(30)).scalars().all()),
        "communication_entries": list(session.execute(select(InspCommunicationEntry).order_by(InspCommunicationEntry.id.desc()).limit(30)).scalars().all()),
        "audit_logs": list(session.execute(select(InspAuditLog).order_by(InspAuditLog.id.desc()).limit(50)).scalars().all()),
        "defect_deadlines": list(session.execute(select(InspDefectDeadline).order_by(InspDefectDeadline.id.desc()).limit(30)).scalars().all()),
        "approval_steps": list(session.execute(select(InspApprovalStep).order_by(InspApprovalStep.id.desc()).limit(30)).scalars().all()),
        "notifications": list(session.execute(select(InspNotification).order_by(InspNotification.id.desc()).limit(30)).scalars().all()),
        "inspection_cycles": list(session.execute(select(InspInspectionCycle).order_by(InspInspectionCycle.id.desc()).limit(30)).scalars().all()),
        "backup_runs": list(session.execute(select(InspBackupRun).order_by(InspBackupRun.id.desc()).limit(30)).scalars().all()),
    }
