import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today


CLOSED_STATUSES = {"Reconciled", "Closed"}


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    data = get_data(filters)
    summary = get_report_summary(data)

    return columns, data, None, None, summary


def get_columns():
    return [
        {
            "label": _("Payment Tracker"),
            "fieldname": "payment_tracker",
            "fieldtype": "Link",
            "options": "PEPL Payment Tracker",
            "width": 150,
        },
        {
            "label": _("Sales Invoice"),
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 145,
        },
        {
            "label": _("Sales Order"),
            "fieldname": "sales_order",
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 145,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 190,
        },
        {
            "label": _("Sector"),
            "fieldname": "sector",
            "fieldtype": "Data",
            "width": 95,
        },
        {
            "label": _("Payment Status"),
            "fieldname": "payment_status",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Invoice Date"),
            "fieldname": "invoice_date",
            "fieldtype": "Date",
            "width": 105,
        },
        {
            "label": _("Due Date"),
            "fieldname": "due_date",
            "fieldtype": "Date",
            "width": 105,
        },
        {
            "label": _("Invoice Amount"),
            "fieldname": "invoice_amount",
            "fieldtype": "Currency",
            "width": 125,
        },
        {
            "label": _("Bank Credit Received"),
            "fieldname": "total_amount_received",
            "fieldtype": "Currency",
            "width": 145,
        },
        {
            "label": _("Gross Payment Realised"),
            "fieldname": "gross_payment_realised",
            "fieldtype": "Currency",
            "width": 145,
        },
        {
            "label": _("Recoverable Held"),
            "fieldname": "total_recoverable_held",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Written Off"),
            "fieldname": "total_written_off",
            "fieldtype": "Currency",
            "width": 110,
        },
        {
            "label": _("Tracker Outstanding"),
            "fieldname": "tracker_outstanding",
            "fieldtype": "Currency",
            "width": 135,
        },
        {
            "label": _("ERPNext Outstanding"),
            "fieldname": "erpnext_outstanding",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": _("Outstanding Difference"),
            "fieldname": "outstanding_difference",
            "fieldtype": "Currency",
            "width": 145,
        },
        {
            "label": _("Invoice Age"),
            "fieldname": "invoice_age_days",
            "fieldtype": "Int",
            "width": 95,
        },
        {
            "label": _("Days Overdue"),
            "fieldname": "days_overdue",
            "fieldtype": "Int",
            "width": 95,
        },
        {
            "label": _("Ageing Bucket"),
            "fieldname": "ageing_bucket",
            "fieldtype": "Data",
            "width": 165,
        },
        {
            "label": _("MSME 45-Day Breach"),
            "fieldname": "msme_breach",
            "fieldtype": "Check",
            "width": 125,
        },
        {
            "label": _("Dispatch Date"),
            "fieldname": "dispatch_date",
            "fieldtype": "Date",
            "width": 105,
        },
        {
            "label": _("Bills Submitted"),
            "fieldname": "bills_submission_date",
            "fieldtype": "Date",
            "width": 115,
        },
        {
            "label": _("R-Note"),
            "fieldname": "rnote_number",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("I-Note"),
            "fieldname": "inote_number",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("JCC"),
            "fieldname": "jcc_number",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("CO7"),
            "fieldname": "co7_number",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Last Update"),
            "fieldname": "last_update_date",
            "fieldtype": "Date",
            "width": 105,
        },
    ]


def get_data(filters):
    tracker_filters = {}

    if filters.get("payment_tracker"):
        tracker_filters["name"] = filters.payment_tracker

    if filters.get("sales_invoice"):
        tracker_filters["linked_sales_invoice"] = filters.sales_invoice

    if filters.get("sales_order"):
        tracker_filters["linked_sales_order"] = filters.sales_order

    if filters.get("customer"):
        tracker_filters["customer"] = filters.customer

    if filters.get("sector"):
        tracker_filters["sector"] = filters.sector

    if filters.get("payment_status"):
        tracker_filters["payment_status"] = filters.payment_status

    if filters.get("ageing_bucket"):
        tracker_filters["ageing_bucket"] = filters.ageing_bucket

    if filters.get("outstanding_only"):
        tracker_filters["total_outstanding"] = [">", 0]

    trackers = frappe.get_all(
        "PEPL Payment Tracker",
        filters=tracker_filters,
        fields=[
            "name",
            "linked_sales_invoice",
            "linked_sales_order",
            "customer",
            "sector",
            "payment_status",
            "invoice_date",
            "invoice_amount",
            "total_amount_received",
            "gross_payment_realised",
            "total_recoverable_held",
            "total_written_off",
            "total_outstanding",
            "days_outstanding",
            "ageing_bucket",
            "dispatch_date",
            "bills_submission_date",
            "rnote_number",
            "inote_number",
            "jcc_number",
            "co7_number",
            "last_update_date",
        ],
        order_by="days_outstanding desc, modified desc",
        limit_page_length=0,
    )

    if not trackers:
        return []

    invoice_names = [
        row.linked_sales_invoice
        for row in trackers
        if row.linked_sales_invoice
    ]

    invoices = []

    if invoice_names:
        invoices = frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", invoice_names]},
            fields=[
                "name",
                "due_date",
                "outstanding_amount",
                "status",
                "docstatus",
            ],
            limit_page_length=0,
        )

    invoice_map = {
        row.name: row
        for row in invoices
    }

    current_date = getdate(today())
    minimum_days_overdue = int(
        filters.get("minimum_days_overdue") or 0
    )

    data = []

    for tracker in trackers:
        invoice = invoice_map.get(tracker.linked_sales_invoice)

        due_date = invoice.due_date if invoice else None
        invoice_age_days = 0
        days_overdue = 0

        if tracker.invoice_date:
            invoice_age_days = max(
                date_diff(
                    current_date,
                    getdate(tracker.invoice_date),
                ),
                0,
            )

        if (
            due_date
            and flt(tracker.total_outstanding) > 0
            and tracker.payment_status not in CLOSED_STATUSES
        ):
            days_overdue = max(
                date_diff(current_date, getdate(due_date)),
                0,
            )

        if days_overdue < minimum_days_overdue:
            continue

        if filters.get("overdue_only") and days_overdue <= 0:
            continue

        if filters.get("msme_breach_only") and invoice_age_days <= 45:
            continue

        erpnext_outstanding = (
            flt(invoice.outstanding_amount)
            if invoice
            else 0
        )

        tracker_outstanding = flt(tracker.total_outstanding)

        data.append(
            {
                "payment_tracker": tracker.name,
                "sales_invoice": tracker.linked_sales_invoice,
                "sales_order": tracker.linked_sales_order,
                "customer": tracker.customer,
                "sector": tracker.sector,
                "payment_status": tracker.payment_status,
                "invoice_date": tracker.invoice_date,
                "due_date": due_date,
                "invoice_amount": tracker.invoice_amount,
                "total_amount_received":
                    tracker.total_amount_received,
                "gross_payment_realised":
                    tracker.gross_payment_realised,
                "total_recoverable_held":
                    tracker.total_recoverable_held,
                "total_written_off":
                    tracker.total_written_off,
                "tracker_outstanding":
                    tracker_outstanding,
                "erpnext_outstanding":
                    erpnext_outstanding,
                "outstanding_difference":
                    tracker_outstanding
                    - erpnext_outstanding,
                "invoice_age_days": invoice_age_days,
                "days_overdue": days_overdue,
                "ageing_bucket": tracker.ageing_bucket,
                "msme_breach": 1
                    if (
                        invoice_age_days > 45
                        and tracker_outstanding > 0
                        and tracker.payment_status
                        not in CLOSED_STATUSES
                    )
                    else 0,
                "dispatch_date": tracker.dispatch_date,
                "bills_submission_date":
                    tracker.bills_submission_date,
                "rnote_number": tracker.rnote_number,
                "inote_number": tracker.inote_number,
                "jcc_number": tracker.jcc_number,
                "co7_number": tracker.co7_number,
                "last_update_date": tracker.last_update_date,
            }
        )

    return data


def get_report_summary(data):
    total_invoice_amount = sum(
        flt(row.get("invoice_amount"))
        for row in data
    )

    total_tracker_outstanding = sum(
        flt(row.get("tracker_outstanding"))
        for row in data
    )

    overdue_amount = sum(
        flt(row.get("tracker_outstanding"))
        for row in data
        if (row.get("days_overdue") or 0) > 0
    )

    breach_amount = sum(
        flt(row.get("tracker_outstanding"))
        for row in data
        if row.get("msme_breach")
    )

    overdue_rows = sum(
        1
        for row in data
        if (row.get("days_overdue") or 0) > 0
    )

    breach_rows = sum(
        1
        for row in data
        if row.get("msme_breach")
    )

    return [
        {
            "value": len(data),
            "label": _("Trackers"),
            "datatype": "Int",
        },
        {
            "value": total_invoice_amount,
            "label": _("Invoice Value"),
            "datatype": "Currency",
        },
        {
            "value": total_tracker_outstanding,
            "label": _("Total Outstanding"),
            "datatype": "Currency",
            "indicator": "Orange",
        },
        {
            "value": overdue_rows,
            "label": _("Overdue Invoices"),
            "datatype": "Int",
            "indicator": "Red",
        },
        {
            "value": overdue_amount,
            "label": _("Overdue Amount"),
            "datatype": "Currency",
            "indicator": "Red",
        },
        {
            "value": breach_rows,
            "label": _("MSME Breaches"),
            "datatype": "Int",
            "indicator": "Red",
        },
        {
            "value": breach_amount,
            "label": _("MSME Breach Amount"),
            "datatype": "Currency",
            "indicator": "Red",
        },
    ]
