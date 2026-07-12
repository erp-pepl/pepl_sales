import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    data = get_data(filters)
    summary = get_report_summary(data)

    return columns, data, None, None, summary


def get_columns():
    return [
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
            "label": _("SO Date"),
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": _("SO Status"),
            "fieldname": "sales_order_status",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("SO Value"),
            "fieldname": "sales_order_value",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Tender"),
            "fieldname": "tender",
            "fieldtype": "Link",
            "options": "PEPL Tender",
            "width": 145,
        },
        {
            "label": _("Tender Status"),
            "fieldname": "tender_status",
            "fieldtype": "Data",
            "width": 115,
        },
        {
            "label": _("Sector"),
            "fieldname": "sector",
            "fieldtype": "Data",
            "width": 95,
        },
        {
            "label": _("PSD Tracker"),
            "fieldname": "psd_tracker",
            "fieldtype": "Link",
            "options": "PEPL PSD Tracker",
            "width": 145,
        },
        {
            "label": _("Active PSD Entries"),
            "fieldname": "active_psd_entries",
            "fieldtype": "Int",
            "width": 115,
        },
        {
            "label": _("PSD Locked"),
            "fieldname": "total_psd_amount",
            "fieldtype": "Currency",
            "width": 115,
        },
        {
            "label": _("Document Tracker"),
            "fieldname": "document_tracker",
            "fieldtype": "Link",
            "options": "PEPL Document Tracker",
            "width": 150,
        },
        {
            "label": _("Required Docs"),
            "fieldname": "required_documents",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("Pending Docs"),
            "fieldname": "pending_documents",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("Material Receipt"),
            "fieldname": "material_receipt_status",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Sales Invoice"),
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 145,
        },
        {
            "label": _("Invoice Count"),
            "fieldname": "invoice_count",
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "label": _("Invoice Status"),
            "fieldname": "invoice_status",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Invoice Value"),
            "fieldname": "invoice_value",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Invoice Outstanding"),
            "fieldname": "invoice_outstanding",
            "fieldtype": "Currency",
            "width": 135,
        },
        {
            "label": _("Payment Tracker"),
            "fieldname": "payment_tracker",
            "fieldtype": "Link",
            "options": "PEPL Payment Tracker",
            "width": 150,
        },
        {
            "label": _("Payment Tracker Count"),
            "fieldname": "payment_tracker_count",
            "fieldtype": "Int",
            "width": 115,
        },
        {
            "label": _("Payment Status"),
            "fieldname": "payment_status",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Payment Outstanding"),
            "fieldname": "payment_outstanding",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": _("Ageing"),
            "fieldname": "ageing_bucket",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Cycle Status"),
            "fieldname": "cycle_status",
            "fieldtype": "Data",
            "width": 175,
        },
        {
            "label": _("Missing Stage"),
            "fieldname": "missing_stage",
            "fieldtype": "Data",
            "width": 190,
        },
    ]


def get_data(filters):
    sales_order_filters = {
        "docstatus": ["<", 2],
    }

    if filters.get("sales_order"):
        sales_order_filters["name"] = filters.sales_order

    if filters.get("customer"):
        sales_order_filters["customer"] = filters.customer

    if filters.get("sales_order_status"):
        sales_order_filters["status"] = filters.sales_order_status

    if filters.get("from_date") and filters.get("to_date"):
        sales_order_filters["transaction_date"] = [
            "between",
            [filters.from_date, filters.to_date],
        ]
    elif filters.get("from_date"):
        sales_order_filters["transaction_date"] = [
            ">=",
            filters.from_date,
        ]
    elif filters.get("to_date"):
        sales_order_filters["transaction_date"] = [
            "<=",
            filters.to_date,
        ]

    sales_orders = frappe.get_all(
        "Sales Order",
        filters=sales_order_filters,
        fields=[
            "name",
            "customer",
            "transaction_date",
            "status",
            "grand_total",
        ],
        order_by="transaction_date desc, modified desc",
        limit_page_length=0,
    )

    if not sales_orders:
        return []

    sales_order_names = [row.name for row in sales_orders]

    tenders = frappe.get_all(
        "PEPL Tender",
        filters={
            "linked_sales_order": ["in", sales_order_names],
        },
        fields=[
            "name",
            "linked_sales_order",
            "status",
            "sector",
        ],
        limit_page_length=0,
    )

    tender_by_so = {
        row.linked_sales_order: row
        for row in tenders
    }

    psd_trackers = frappe.get_all(
        "PEPL PSD Tracker",
        filters={
            "linked_sales_order": ["in", sales_order_names],
        },
        fields=[
            "name",
            "linked_sales_order",
            "active_entries_count",
            "total_psd_amount",
        ],
        limit_page_length=0,
    )

    psd_by_so = {
        row.linked_sales_order: row
        for row in psd_trackers
    }

    document_trackers = frappe.get_all(
        "PEPL Document Tracker",
        filters={
            "linked_sales_order": ["in", sales_order_names],
        },
        fields=[
            "name",
            "linked_sales_order",
        ],
        limit_page_length=0,
    )

    document_by_so = {
        row.linked_sales_order: row
        for row in document_trackers
    }

    document_entries = []

    if document_trackers:
        document_entries = frappe.get_all(
            "PEPL Document Entry",
            filters={
                "parent": [
                    "in",
                    [row.name for row in document_trackers],
                ],
                "parenttype": "PEPL Document Tracker",
            },
            fields=[
                "parent",
                "document_type",
                "document_status",
                "is_required",
            ],
            limit_page_length=0,
        )

    document_summary = {}

    for entry in document_entries:
        summary = document_summary.setdefault(
            entry.parent,
            {
                "required": 0,
                "pending": 0,
                "material_receipt": "Not Configured",
            },
        )

        if entry.is_required:
            summary["required"] += 1

        if (
            entry.is_required
            and entry.document_status
            not in {"Received", "Filed"}
        ):
            summary["pending"] += 1

        if entry.document_type == "Material Receipt":
            summary["material_receipt"] = (
                entry.document_status or "Pending"
            )

    invoice_items = frappe.get_all(
        "Sales Invoice Item",
        filters={
            "sales_order": ["in", sales_order_names],
            "docstatus": ["<", 2],
        },
        fields=[
            "parent",
            "sales_order",
        ],
        order_by="creation desc",
        limit_page_length=0,
    )

    invoice_names = list(
        {
            row.parent
            for row in invoice_items
            if row.parent
        }
    )

    invoices = []

    if invoice_names:
        invoices = frappe.get_all(
            "Sales Invoice",
            filters={
                "name": ["in", invoice_names],
                "docstatus": ["<", 2],
            },
            fields=[
                "name",
                "status",
                "grand_total",
                "outstanding_amount",
                "posting_date",
            ],
            order_by="posting_date desc, modified desc",
            limit_page_length=0,
        )

    invoice_map = {
        row.name: row
        for row in invoices
    }

    invoices_by_so = {}

    for item in invoice_items:
        invoice = invoice_map.get(item.parent)

        if not invoice or not item.sales_order:
            continue

        sales_order_invoices = invoices_by_so.setdefault(
            item.sales_order,
            [],
        )

        if not any(
            existing.name == invoice.name
            for existing in sales_order_invoices
        ):
            sales_order_invoices.append(invoice)

    payment_trackers = []

    if invoice_names:
        payment_trackers = frappe.get_all(
            "PEPL Payment Tracker",
            filters={
                "linked_sales_invoice": ["in", invoice_names],
            },
            fields=[
                "name",
                "linked_sales_invoice",
                "payment_status",
                "total_outstanding",
                "ageing_bucket",
            ],
            order_by="modified desc",
            limit_page_length=0,
        )

    payments_by_invoice = {}

    for payment in payment_trackers:
        payments_by_invoice.setdefault(
            payment.linked_sales_invoice,
            [],
        ).append(payment)

    data = []

    for sales_order in sales_orders:
        tender = tender_by_so.get(sales_order.name)
        psd = psd_by_so.get(sales_order.name)
        document_tracker = document_by_so.get(
            sales_order.name
        )
        invoice_rows = invoices_by_so.get(
            sales_order.name,
            [],
        )

        invoice_rows = sorted(
            invoice_rows,
            key=lambda row: (
                row.posting_date or "",
                row.name,
            ),
            reverse=True,
        )

        latest_invoice = (
            invoice_rows[0]
            if invoice_rows
            else None
        )

        payment_rows = []

        for invoice_row in invoice_rows:
            payment_rows.extend(
                payments_by_invoice.get(
                    invoice_row.name,
                    [],
                )
            )

        payment_rows = sorted(
            payment_rows,
            key=lambda row: row.name,
            reverse=True,
        )

        latest_payment = (
            payment_rows[0]
            if payment_rows
            else None
        )

        invoice_value = sum(
            flt(row.grand_total)
            for row in invoice_rows
        )

        invoice_outstanding = sum(
            flt(row.outstanding_amount)
            for row in invoice_rows
        )

        payment_outstanding = sum(
            flt(row.total_outstanding)
            for row in payment_rows
        )

        doc_summary = (
            document_summary.get(document_tracker.name)
            if document_tracker
            else None
        ) or {
            "required": 0,
            "pending": 0,
            "material_receipt": "Not Configured",
        }

        missing_stages = []

        if not tender:
            missing_stages.append("Tender Link")

        if not psd:
            missing_stages.append("PSD Tracker")

        if not document_tracker:
            missing_stages.append("Document Tracker")

        if (
            document_tracker
            and doc_summary["material_receipt"]
            not in {"Received", "Filed"}
        ):
            missing_stages.append("Material Receipt")

        if not invoice_rows:
            missing_stages.append("Sales Invoice")

        if invoice_rows and len(payment_rows) < len(invoice_rows):
            missing_stages.append("Payment Tracker")

        if invoice_rows and invoice_outstanding <= 0:
            cycle_status = "Payment Complete"
        elif payment_rows:
            cycle_status = "Payment Pending"
        elif invoice_rows:
            cycle_status = "Invoice Raised"
        elif document_tracker or psd:
            cycle_status = "Order Execution"
        else:
            cycle_status = "Sales Order Created"

        row = {
            "sales_order": sales_order.name,
            "customer": sales_order.customer,
            "transaction_date": sales_order.transaction_date,
            "sales_order_status": sales_order.status,
            "sales_order_value": sales_order.grand_total,
            "tender": tender.name if tender else None,
            "tender_status": tender.status if tender else None,
            "sector": tender.sector if tender else None,
            "psd_tracker": psd.name if psd else None,
            "active_psd_entries":
                psd.active_entries_count if psd else 0,
            "total_psd_amount":
                psd.total_psd_amount if psd else 0,
            "document_tracker":
                document_tracker.name
                if document_tracker
                else None,
            "required_documents": doc_summary["required"],
            "pending_documents": doc_summary["pending"],
            "material_receipt_status":
                doc_summary["material_receipt"],
            "sales_invoice":
                latest_invoice.name
                if latest_invoice
                else None,
            "invoice_count": len(invoice_rows),
            "invoice_status": (
                latest_invoice.status
                if len(invoice_rows) == 1
                else "Multiple"
                if invoice_rows
                else None
            ),
            "invoice_value": invoice_value,
            "invoice_outstanding": invoice_outstanding,
            "payment_tracker":
                latest_payment.name
                if latest_payment
                else None,
            "payment_tracker_count": len(payment_rows),
            "payment_status": (
                latest_payment.payment_status
                if len(payment_rows) == 1
                else "Multiple"
                if payment_rows
                else None
            ),
            "payment_outstanding": payment_outstanding,
            "ageing_bucket": (
                latest_payment.ageing_bucket
                if len(payment_rows) == 1
                else "Multiple"
                if payment_rows
                else None
            ),
            "cycle_status": cycle_status,
            "missing_stage": (
                ", ".join(missing_stages)
                if missing_stages
                else ""
            ),
        }

        if filters.get("sector") and row["sector"] != filters.sector:
            continue

        if (
            filters.get("cycle_status")
            and row["cycle_status"] != filters.cycle_status
        ):
            continue

        if filters.get("missing_only") and not row["missing_stage"]:
            continue

        if (
            filters.get("outstanding_only")
            and flt(row["payment_outstanding"]) <= 0
            and flt(row["invoice_outstanding"]) <= 0
        ):
            continue

        data.append(row)

    return data


def get_report_summary(data):
    so_value = sum(
        flt(row.get("sales_order_value"))
        for row in data
    )

    invoice_value = sum(
        flt(row.get("invoice_value"))
        for row in data
    )

    outstanding = sum(
        flt(row.get("payment_outstanding"))
        or flt(row.get("invoice_outstanding"))
        for row in data
    )

    complete = sum(
        1
        for row in data
        if row.get("cycle_status") == "Payment Complete"
    )

    missing = sum(
        1
        for row in data
        if row.get("missing_stage")
    )

    return [
        {
            "value": len(data),
            "label": _("Sales Orders"),
            "datatype": "Int",
        },
        {
            "value": so_value,
            "label": _("Sales Order Value"),
            "datatype": "Currency",
        },
        {
            "value": invoice_value,
            "label": _("Invoice Value"),
            "datatype": "Currency",
        },
        {
            "value": outstanding,
            "label": _("Outstanding"),
            "datatype": "Currency",
            "indicator": "Orange",
        },
        {
            "value": complete,
            "label": _("Payment Complete"),
            "datatype": "Int",
            "indicator": "Green",
        },
        {
            "value": missing,
            "label": _("Rows with Missing Stages"),
            "datatype": "Int",
            "indicator": "Red",
        },
    ]
