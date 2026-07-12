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
            "label": _("Document Type"),
            "fieldname": "document_type",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 230,
        },
        {
            "label": _("Required"),
            "fieldname": "is_required",
            "fieldtype": "Check",
            "width": 75,
        },
        {
            "label": _("Status"),
            "fieldname": "document_status",
            "fieldtype": "Data",
            "width": 95,
        },
        {
            "label": _("Direction"),
            "fieldname": "direction",
            "fieldtype": "Data",
            "width": 165,
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
            "label": _("Reference Number"),
            "fieldname": "reference_number",
            "fieldtype": "Data",
            "width": 135,
        },
        {
            "label": _("Source"),
            "fieldname": "source",
            "fieldtype": "Data",
            "width": 155,
        },
        {
            "label": _("Primary File"),
            "fieldname": "primary_attachment",
            "fieldtype": "Attach",
            "width": 115,
        },
        {
            "label": _("Receipt Proof"),
            "fieldname": "receipt_attachment",
            "fieldtype": "Attach",
            "width": 115,
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
    }

    if filters.get("document_type"):
        entry_filters["document_type"] = filters.document_type

    if filters.get("document_status"):
        entry_filters["document_status"] = filters.document_status
    else:
        entry_filters["document_status"] = ["not in", list(COMPLETED_STATUSES)]

    if filters.get("required_only"):
        entry_filters["is_required"] = 1

    if filters.get("direction"):
        entry_filters["direction"] = filters.direction

    entries = frappe.get_all(
        "PEPL Document Entry",
        filters=entry_filters,
        fields=[
            "name",
            "parent",
            "document_date",
            "document_type",
            "description",
            "primary_attachment",
            "reference_number",
            "direction",
            "document_status",
            "source",
            "source_reference",
            "is_required",
            "received_date",
            "received_by",
            "receipt_attachment",
            "remarks",
            "creation",
        ],
        order_by="document_date asc, creation asc",
        limit_page_length=0,
    )

    current_date = getdate(today())
    minimum_pending_days = int(filters.get("minimum_pending_days") or 0)

    data = []

    for entry in entries:
        tracker = tracker_map.get(entry.parent)

        if not tracker:
            continue

        base_date = entry.document_date or entry.creation
        pending_days = 0

        if base_date:
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
                "document_type": entry.document_type,
                "description": entry.description,
                "is_required": entry.is_required,
                "document_status": entry.document_status,
                "direction": entry.direction,
                "document_date": entry.document_date,
                "pending_days": pending_days,
                "reference_number": entry.reference_number,
                "source": entry.source,
                "primary_attachment": entry.primary_attachment,
                "receipt_attachment": entry.receipt_attachment,
                "received_date": entry.received_date,
                "received_by": entry.received_by,
                "remarks": entry.remarks,
            }
        )

    return data


def get_report_summary(data):
    required_pending = sum(
        1
        for row in data
        if row.get("is_required")
    )

    pending_over_30 = sum(
        1
        for row in data
        if (row.get("pending_days") or 0) > 30
    )

    customers = {
        row.get("customer")
        for row in data
        if row.get("customer")
    }

    sales_orders = {
        row.get("sales_order")
        for row in data
        if row.get("sales_order")
    }

    return [
        {
            "value": len(data),
            "label": _("Pending Documents"),
            "datatype": "Int",
        },
        {
            "value": required_pending,
            "label": _("Required Pending"),
            "datatype": "Int",
            "indicator": "Orange",
        },
        {
            "value": pending_over_30,
            "label": _("Pending Over 30 Days"),
            "datatype": "Int",
            "indicator": "Red",
        },
        {
            "value": len(customers),
            "label": _("Customers"),
            "datatype": "Int",
        },
        {
            "value": len(sales_orders),
            "label": _("Sales Orders"),
            "datatype": "Int",
        },
    ]
