from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from elektrocalc.db.models import (
    InspAppointment,
    InspCustomer,
    InspDistribution,
    InspDistributionReport,
    InspDefect,
    InspInspectionOrder,
    InspInspectionOrderDistribution,
    InspMeasurement,
    InspMeasurementSet,
    InspInvoice,
    InspMeasuringDevice,
    InspDocument,
    InspCommunicationEntry,
    InspAuditLog,
    InspDefectDeadline,
    InspApprovalStep,
    InspNotification,
    InspInspectionCycle,
    InspBackupRun,
    InspThermographyEntry,
    InspDeviceCalibration,
    InspNumberSequence,
    InspPaymentEntry,
    InspDataRetentionRule,
    InspRestoreTest,
    InspObject,
    InspPortalRelease,
    InspReport,
    InspSite,
    InspTask,
    InspTenant,
)
from elektrocalc.services.inspection import (
    add_distribution,
    assign_distribution_to_order,
    create_appointment,
    create_customer,
    create_distribution_report,
    create_defect,
    update_defect_status,
    create_inspection_order,
    create_measurement,
    create_measurement_set,
    create_object,
    create_portal_release,
    create_report,
    create_task,
    update_task_status,
    create_tenant,
    create_invoice,
    update_invoice_total,
    update_invoice_status,
    create_measuring_device,
    create_document_record,
    create_communication_entry,
    log_audit,
    update_inspection_order_status,
    update_report_status,
    create_defect_deadline,
    create_approval_step,
    update_approval_step_status,
    create_notification,
    update_notification_status,
    create_inspection_cycle,
    create_backup_run,
    create_thermography_entry,
    create_device_calibration,
    create_number_sequence,
    issue_next_number,
    create_payment_entry,
    create_data_retention_rule,
    create_restore_test,
)


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    insp_tables = [
        InspTenant.__table__,
        InspCustomer.__table__,
        InspSite.__table__,
        InspObject.__table__,
        InspDistribution.__table__,
        InspInspectionOrder.__table__,
        InspInspectionOrderDistribution.__table__,
        InspAppointment.__table__,
        InspMeasurementSet.__table__,
        InspMeasurement.__table__,
        InspDefect.__table__,
        InspReport.__table__,
        InspDistributionReport.__table__,
        InspTask.__table__,
        InspInvoice.__table__,
        InspMeasuringDevice.__table__,
        InspDocument.__table__,
        InspCommunicationEntry.__table__,
        InspAuditLog.__table__,
        InspDefectDeadline.__table__,
        InspApprovalStep.__table__,
        InspNotification.__table__,
        InspInspectionCycle.__table__,
        InspBackupRun.__table__,
        InspThermographyEntry.__table__,
        InspDeviceCalibration.__table__,
        InspNumberSequence.__table__,
        InspPaymentEntry.__table__,
        InspDataRetentionRule.__table__,
        InspRestoreTest.__table__,
        InspPortalRelease.__table__,
    ]
    for table in insp_tables:
        table.create(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def test_assign_distribution_rejects_foreign_object():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")

    obj1 = create_object(s, customer.id, "S1", "Obj 1")
    obj2 = create_object(s, customer.id, "S2", "Obj 2")

    dist_other = add_distribution(s, obj2.id, "UV-2")
    order = create_inspection_order(s, obj1.id, "Wiederholungsprüfung")

    try:
        assign_distribution_to_order(s, order.id, dist_other.id)
    except ValueError as exc:
        assert "gehört nicht zum Objekt" in str(exc)
    else:
        raise AssertionError("Expected ValueError for cross-object distribution assignment")


def test_create_report_rejects_second_main_report():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Erstprüfung")

    create_report(s, order.id, "Hauptbericht v1")

    try:
        create_report(s, order.id, "Hauptbericht v2")
    except ValueError as exc:
        assert "existiert bereits" in str(exc)
    else:
        raise AssertionError("Expected ValueError for duplicate report")


def test_create_object_reuses_existing_site_name_per_customer():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")

    first = create_object(s, customer.id, "Standort A", "Objekt A")
    second = create_object(s, customer.id, "Standort A", "Objekt B")

    assert first.site_id == second.site_id


def test_appointment_rejects_end_before_start():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Erstprüfung")

    try:
        create_appointment(s, order.id, "2026-04-07T10:00", "2026-04-07T09:00")
    except ValueError as exc:
        assert "vor dem Start" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid appointment range")


def test_create_measurement_task_and_portal_release():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Wiederholungsprüfung")
    report = create_report(s, order.id, "Hauptbericht")

    ms = create_measurement_set(s, order.id, "RCD-Set")
    m = create_measurement(s, ms.id, "RCD-01", "0.28", "s")
    t = create_task(s, tenant.id, "Rückfrage klären", obj.id, None, report.id)
    r = create_portal_release(s, customer.id, "report", report.id)

    assert m.measurement_set_id == ms.id
    assert t.tenant_id == tenant.id
    assert r.customer_id == customer.id


def test_distribution_report_requires_order_distribution_link():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Wiederholungsprüfung")
    dist = add_distribution(s, obj.id, "UV-1")
    report = create_report(s, order.id, "Hauptbericht")

    try:
        create_distribution_report(s, report.id, dist.id, "Kurzfazit")
    except ValueError as exc:
        assert "nicht zugeordnet" in str(exc)
    else:
        raise AssertionError("Expected ValueError without order-distribution assignment")

    assign_distribution_to_order(s, order.id, dist.id)
    d_report = create_distribution_report(s, report.id, dist.id, "Kurzfazit")
    assert d_report.report_id == report.id


def test_portal_release_rejects_foreign_customer_target():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    c1 = create_customer(s, tenant.id, "C1")
    c2 = create_customer(s, tenant.id, "C2")
    obj = create_object(s, c1.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Erstprüfung")
    report = create_report(s, order.id, "Hauptbericht")

    try:
        create_portal_release(s, c2.id, "report", report.id)
    except ValueError as exc:
        assert "gehört nicht zum Kunden" in str(exc)
    else:
        raise AssertionError("Expected ValueError for cross-customer portal release")


def test_invoice_finalization_locks_amount_and_status_flow():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Erstprüfung")

    inv = create_invoice(s, order.id, 12000)
    inv = update_invoice_total(s, inv.id, 15000)
    assert inv.total_cent == 15000

    inv = update_invoice_status(s, inv.id, "freigegeben")
    inv = update_invoice_status(s, inv.id, "finalisiert")
    assert inv.status == "finalisiert"

    try:
        update_invoice_total(s, inv.id, 99999)
    except ValueError as exc:
        assert "Finalisierung" in str(exc)
    else:
        raise AssertionError("Expected ValueError after finalization")


def test_device_document_communication_and_audit_modules():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Wiederholungsprüfung")
    defect = create_defect(s, order.id, "Isolationswert auffällig", None)
    report = create_report(s, order.id, "Hauptbericht")
    task = create_task(s, tenant.id, "Rückfrage", obj.id, defect.id, report.id)

    dev = create_measuring_device(s, tenant.id, "Profitest", "SN-123", "2026-12-31")
    doc = create_document_record(
        s,
        tenant_id=tenant.id,
        file_name="bericht.pdf",
        category="report",
        visibility="internal",
        object_id=obj.id,
        inspection_order_id=order.id,
        defect_id=defect.id,
        report_id=report.id,
    )
    comm = create_communication_entry(
        s,
        tenant_id=tenant.id,
        message="Bitte Nachweis bis Freitag hochladen.",
        direction="outbound",
        task_id=task.id,
        customer_id=customer.id,
    )
    audit = log_audit(s, tenant.id, "manual_test_log", "task", task.id, actor="tester")

    assert dev.tenant_id == tenant.id
    assert doc.report_id == report.id
    assert comm.task_id == task.id
    assert audit.action == "manual_test_log"


def test_order_and_report_status_workflow_and_locking_distribution_report():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Wiederholungsprüfung")
    dist = add_distribution(s, obj.id, "UV-1")
    assign_distribution_to_order(s, order.id, dist.id)
    report = create_report(s, order.id, "Hauptbericht")

    order = update_inspection_order_status(s, order.id, "in_progress")
    order = update_inspection_order_status(s, order.id, "technical_done")
    order = update_inspection_order_status(s, order.id, "finalized")
    assert order.status == "finalized"

    report = update_report_status(s, report.id, "for_approval")
    report = update_report_status(s, report.id, "approved")
    report = update_report_status(s, report.id, "finalized")
    assert report.status == "finalized"

    try:
        create_distribution_report(s, report.id, dist.id, "Zu spät")
    except ValueError as exc:
        assert "nach Finalisierung" in str(exc)
    else:
        raise AssertionError("Expected ValueError for distribution report after finalization")


def test_measurement_locked_after_order_finalized():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Wiederholungsprüfung")
    ms = create_measurement_set(s, order.id, "Set A")

    update_inspection_order_status(s, order.id, "in_progress")
    update_inspection_order_status(s, order.id, "technical_done")
    update_inspection_order_status(s, order.id, "finalized")

    try:
        create_measurement(s, ms.id, "P1", "1.0", "Ohm")
    except ValueError as exc:
        assert "finalisiertem Prüfauftrag" in str(exc)
    else:
        raise AssertionError("Expected ValueError for measurement after order finalization")


def test_next_five_blocks_deadline_approval_notification_cycle_backup():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Wiederholungsprüfung")
    defect = create_defect(s, order.id, "Sichtprüfung offen", None)
    report = create_report(s, order.id, "Hauptbericht")

    ddl = create_defect_deadline(s, defect.id, "2026-12-31", "Nachweis erforderlich")
    step = create_approval_step(s, tenant.id, "report", report.id, "admin")
    step = update_approval_step_status(s, step.id, "approved")
    note = create_notification(s, tenant.id, "Frist", "Frist läuft in 7 Tagen ab", "DEFECT", defect.id)
    cycle = create_inspection_cycle(s, obj.id, 48, "2027-01-31")
    backup = create_backup_run(s, tenant.id, "ok", "/backups/t1.tar.zst", "2026-04-07T10:30:00")

    assert ddl.defect_id == defect.id
    defect_refetched = s.get(InspDefect, defect.id)
    assert defect_refetched.status == "deadline_set"
    assert defect_refetched.due_date.isoformat() == "2026-12-31"
    assert step.status == "approved"
    assert note.related_id == defect.id
    assert note.related_type == "defect"
    assert cycle.object_id == obj.id
    assert backup.status == "ok"


def test_next_six_modules_thermo_calibration_sequences_payment_retention_restore():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Wiederholungsprüfung")
    defect = create_defect(s, order.id, "Warmstelle", None)
    inv = create_invoice(s, order.id, 50000)
    dev = create_measuring_device(s, tenant.id, "Testo", "SN-22", "2026-12-31")
    backup = create_backup_run(s, tenant.id, "ok", "/tmp/bkp", "2026-04-08T08:00:00")

    thermo = create_thermography_entry(s, obj.id, defect.id, "thermo_001.jpg", "84.2")
    calib = create_device_calibration(s, dev.id, "2026-01-10", "2027-01-10", "cert-1")
    seq = create_number_sequence(s, tenant.id, "invoice", "RE-")
    issued = issue_next_number(s, seq.id)
    pay = create_payment_entry(s, inv.id, 25000)
    retention = create_data_retention_rule(s, tenant.id, "report", 3650, "archive")
    restore = create_restore_test(s, tenant.id, backup.id, "passed", "Restore in 12min")

    assert thermo.object_id == obj.id
    assert calib.measuring_device_id == dev.id
    assert issued.startswith("RE-")
    assert pay.invoice_id == inv.id
    assert retention.data_type == "report"
    assert restore.backup_run_id == backup.id


def test_cross_tenant_guards_and_payment_workflow():
    s = _make_session()
    t1 = create_tenant(s, "T1")
    t2 = create_tenant(s, "T2")
    c1 = create_customer(s, t1.id, "C1")
    c2 = create_customer(s, t2.id, "C2")
    o1 = create_object(s, c1.id, "S1", "Obj1")
    o2 = create_object(s, c2.id, "S2", "Obj2")
    ord1 = create_inspection_order(s, o1.id, "Wiederholungsprüfung")
    inv1 = create_invoice(s, ord1.id, 10000)
    inv1 = update_invoice_status(s, inv1.id, "freigegeben")
    inv1 = update_invoice_status(s, inv1.id, "finalisiert")
    inv1 = update_invoice_status(s, inv1.id, "versendet")

    # document cross-tenant guard
    try:
        create_document_record(
            s,
            tenant_id=t1.id,
            file_name="x.pdf",
            category="report",
            visibility="internal",
            object_id=o2.id,
            inspection_order_id=None,
            defect_id=None,
            report_id=None,
        )
    except ValueError as exc:
        assert "gehört nicht zum Mandanten" in str(exc)
    else:
        raise AssertionError("Expected cross-tenant document guard")

    # payment updates invoice to paid when total reached
    create_payment_entry(s, inv1.id, 10000)
    inv1_refetched = s.get(InspInvoice, inv1.id)
    assert inv1_refetched.status == "bezahlt"


def test_restore_test_rejects_invalid_status():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    backup = create_backup_run(s, tenant.id, "ok", "/tmp/bkp", "2026-04-08T08:00:00")

    try:
        create_restore_test(s, tenant.id, backup.id, "unknown", "invalid status")
    except ValueError as exc:
        assert "passed|failed" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid restore-test status")


def test_defect_task_notification_status_workflows():
    s = _make_session()
    tenant = create_tenant(s, "T1")
    customer = create_customer(s, tenant.id, "C1")
    obj = create_object(s, customer.id, "S1", "Obj 1")
    order = create_inspection_order(s, obj.id, "Wiederholungsprüfung")
    defect = create_defect(s, order.id, "Klemmstelle lose", None)
    task = create_task(s, tenant.id, "Nachziehen", obj.id, defect.id, None)
    note = create_notification(s, tenant.id, "Info", "Bitte prüfen", None, None)

    defect = update_defect_status(s, defect.id, "assessed")
    defect = update_defect_status(s, defect.id, "follow_up")
    defect = update_defect_status(s, defect.id, "closed")
    assert defect.status == "closed"

    task = update_task_status(s, task.id, "in_progress")
    task = update_task_status(s, task.id, "done")
    task = update_task_status(s, task.id, "archived")
    assert task.status == "archived"

    note = update_notification_status(s, note.id, "acknowledged")
    note = update_notification_status(s, note.id, "resolved")
    note = update_notification_status(s, note.id, "archived")
    assert note.status == "archived"

    try:
        update_notification_status(s, note.id, "open")
    except ValueError as exc:
        assert "nicht erlaubt" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid notification rollback transition")
