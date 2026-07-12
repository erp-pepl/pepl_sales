import frappe
from frappe import _
from frappe.utils import date_diff, getdate, today


COMPLETED_STATUSES = {"Received", "Filed"}


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    data = get_data(filters)
    summary = get_report_summary(data)

    return columns, data, None, None, summary


def get_columns():
    return [
        {
            "label": _("Document Tracker"),
            "fieldname": "document_tracker",
            "fieldtype": "Link",
            "options": "PEPL Document Tracker",
            "width": 155,
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
            "label": _("Receipt Status"),
            "fieldname": "document_status",
            "fieldtype": "Data",
            "width": 105,
        },
        {
            "label": _("Document Date"),
            "fieldname": "document_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Pending Days"),
            "fieldname": "pending_days",
            "fieldtype": "Int",
            "width": 95,
        },
        {
            "label": _("Required"),
            "fieldname": "is_required",
            "fieldtype": "Check",
            "width": 70,
        },
        {
            "label": _("Receipt Proof"),
            "fieldname": "receipt_attachment",
            "fieldtype": "Attach",
            "width": 120,
        },
        {
            "label": _("Received Date"),
            "fieldname": "received_date",
            "fieldtype": "Date",
            "width": 105,
        },
        {
            "label": _("Received By"),
            "fieldname": "received_by",
            "fieldtype": "Link",
            "options": "User",
            "width": 150,
        },
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
            "label": _("Payment Status"),
            "fieldname": "payment_status",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Dispatch Date"),
            "fieldname": "dispatch_date",
            "fieldtype": "Date",
            "width": 105,
        },
        {
            "label": _("Outstanding"),
            "fieldname": "total_outstanding",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Remarks"),
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 220,
        },
    ]


def get_data(filters):
    tracker_filters = {}

    if filters.get("document_tracker"):
        tracker_filters["name"] = filters.document_tracker

    if filters.get("sales_order"):
        tracker_filters["linked_sales_order"] = filters.sales_order

    if filters.get("customer"):
        tracker_filters["customer"] = filters.customer

    trackers = frappe.get_all(
        "PEPL Document Tracker",
        filters=tracker_filters,
        fields=[
            "name",
            "linked_sales_order",
            "customer",
        ],
        order_by="modified desc",
        limit_page_length=0,
    )

    if not trackers:
        return []

    tracker_map = {
        row.name: row
        for row in trackers
    }

    entry_filters = {
        "parent": ["in", list(tracker_map)],
        "parenttype": "PEPL Document Tracker",
        "document_type": "Material Receipt",
    }

    if filters.get("receipt_status"):
        entry_filters["document_status"] = filters.receipt_status
    elif filters.get("pending_only"):
        entry_filters["document_status"] = [
            "not in",
            list(COMPLETED_STATUSES),
        ]

    entries = frappe.get_all(
        "PEPL Document Entry",
        filters=entry_filters,
        fields=[
            "name",
            "parent",
            "document_date",
            "document_status",
            "is_required",
            "receipt_attachment",
            "received_date",
            "received_by",
            "remarks",
            "creation",
        ],
        order_by="document_date asc, creation asc",
        limit_page_length=0,
    )

    sales_orders = {
        tracker.linked_sales_order
        for tracker in trackers
        if tracker.linked_sales_order
    }

    payment_trackers = []

    if sales_orders:
        payment_filters = {
            "linked_sales_order": ["in", list(sales_orders)],
        }

        if filters.get("payment_status"):
            payment_filters["payment_status"] = filters.payment_status

        payment_trackers = frappe.get_all(
            "PEPL Payment Tracker",
            filters=payment_filters,
            fields=[
                "name",
                "linked_sales_order",
                "linked_sales_invoice",
                "payment_status",
                "dispatch_date",
                "total_outstanding",
            ],
            order_by="modified desc",
            limit_page_length=0,
        )

    payment_by_so = {}

    for payment in payment_trackers:
        if payment.linked_sales_order not in payment_by_so:
            payment_by_so[payment.linked_sales_order] = payment

    current_date = getdate(today())
    minimum_pending_days = int(filters.get("minimum_pending_days") or 0)

    data = []

    for entry in entries:
        tracker = tracker_map.get(entry.parent)

        if not tracker:
            continue

        payment = payment_by_so.get(tracker.linked_sales_order)

        if filters.get("payment_status") and not payment:
            continue

        base_date = entry.document_date or entry.creation
        pending_days = 0

        if (
            entry.document_status not in COMPLETED_STATUSES
            and base_date
        ):
            pending_days = max(
                date_diff(current_date, getdate(base_date)),
                0,
            )

        if pending_days < minimum_pending_days:
            continue

        data.append(
            {
                "document_tracker": tracker.name,
                "sales_order": tracker.linked_sales_order,
                "customer": tracker.customer,
                "document_status": entry.document_status,
                "document_date": entry.document_date,
                "pending_days": pending_days,
                "is_required": entry.is_required,
                "receipt_attachment": entry.receipt_attachment,
                "received_date": entry.received_date,
                "received_by": entry.received_by,
                "payment_tracker": payment.name if payment else None,
                "sales_invoice":
                    payment.linked_sales_invoice
                    if payment
                    else None,
                "payment_status":
                    payment.payment_status
                    if payment
                    else None,
                "dispatch_date":
                    payment.dispatch_date
                    if payment
                    else None,
                "total_outstanding":
                    payment.total_outstanding
                    if payment
                    else 0,
                "remarks": entry.remarks,
            }
        )

    return data


def get_report_summary(data):
    pending = sum(
        1
        for row in data
        if row.get("document_status") not in COMPLETED_STATUSES
    )

    received = sum(
        1
        for row in data
        if row.get("document_status") in COMPLETED_STATUSES
    )

    missing_proof = sum(
        1
        for row in data
        if (
            row.get("document_status") not in COMPLETED_STATUSES
            and not row.get("receipt_attachment")
        )
    )

    pending_over_15 = sum(
        1
        for row in data
        if (row.get("pending_days") or 0) > 15
    )

    return [
        {
            "value": len(data),
            "label": _("Material Receipt Rows"),
            "datatype": "Int",
        },
        {
            "value": pending,
            "label": _("Pending"),
            "datatype": "Int",
            "indicator": "Orange",
        },
        {
            "value": received,
            "label": _("Received"),
            "datatype": "Int",
            "indicator": "Green",
        },
        {
            "value": missing_proof,
            "label": _("Pending Without Proof"),
            "datatype": "Int",
            "indicator": "Red",
        },
        {
            "value": pending_over_15,
            "label": _("Pending Over 15 Days"),
            "datatype": "Int",
            "indicator": "Red",
        },
    ]
