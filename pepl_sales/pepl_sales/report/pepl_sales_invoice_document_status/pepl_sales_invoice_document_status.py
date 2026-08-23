import frappe
from frappe import _


COMPLETED_STATUSES = {
    "Received",
    "Filed",
}

DOCUMENTS = {
    "jcc": {
        "label": "JCC",
        "code": "JCC",
        "types": {
            "JCC",
            "Joint Completion Certificate (JCC)",
        },
        "fallback_sector": "Common",
    },
    "r_note": {
        "label": "R-Note",
        "code": "R_NOTE",
        "types": {
            "R-Note",
        },
        "fallback_sector": "Railways",
    },
    "i_note": {
        "label": "I-Note",
        "code": "I_NOTE",
        "types": {
            "I-Note",
        },
        "fallback_sector": "Defence",
    },
}


def execute(filters=None):
    filters = frappe._dict(
        filters or {}
    )

    columns = get_columns()
    data = get_data(filters)
    summary = get_report_summary(
        data
    )

    return (
        columns,
        data,
        None,
        None,
        summary,
    )


def get_columns():
    return [
        {
            "label": _("Sales Invoice"),
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 145,
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 105,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 190,
        },
        {
            "label": _("Sales Order"),
            "fieldname": "sales_order",
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 145,
        },
        {
            "label": _("Sector"),
            "fieldname": "sector",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Document Tracker"),
            "fieldname": "document_tracker",
            "fieldtype": "Link",
            "options": "PEPL Document Tracker",
            "width": 155,
        },
        {
            "label": _("JCC Status"),
            "fieldname": "jcc_status",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("R-Note Status"),
            "fieldname": "r_note_status",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("I-Note Status"),
            "fieldname": "i_note_status",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Pending Documents"),
            "fieldname": "pending_documents",
            "fieldtype": "Data",
            "width": 260,
        },
        {
            "label": _("Overall Document Status"),
            "fieldname": "overall_status",
            "fieldtype": "Data",
            "width": 155,
        },
        {
            "label": _("Outstanding Amount"),
            "fieldname": "outstanding_amount",
            "fieldtype": "Currency",
            "width": 135,
        },
    ]


def get_data(filters):
    invoice_filters = {
        "docstatus": 1,
    }

    if filters.get("sales_invoice"):
        invoice_filters["name"] = (
            filters.sales_invoice
        )

    if filters.get("customer"):
        invoice_filters["customer"] = (
            filters.customer
        )

    if (
        filters.get("from_date")
        and filters.get("to_date")
    ):
        invoice_filters["posting_date"] = [
            "between",
            [
                filters.from_date,
                filters.to_date,
            ],
        ]
    elif filters.get("from_date"):
        invoice_filters["posting_date"] = [
            ">=",
            filters.from_date,
        ]
    elif filters.get("to_date"):
        invoice_filters["posting_date"] = [
            "<=",
            filters.to_date,
        ]

    invoices = frappe.get_all(
        "Sales Invoice",
        filters=invoice_filters,
        fields=[
            "name",
            "posting_date",
            "customer",
            "outstanding_amount",
        ],
        order_by=(
            "posting_date desc, "
            "creation desc"
        ),
        limit_page_length=0,
    )

    if not invoices:
        return []

    invoice_names = [
        row.name
        for row in invoices
    ]

    item_rows = frappe.get_all(
        "Sales Invoice Item",
        filters={
            "parent": [
                "in",
                invoice_names,
            ],
        },
        fields=[
            "parent",
            "sales_order",
            "idx",
        ],
        order_by="parent asc, idx asc",
        limit_page_length=0,
    )

    sales_orders_by_invoice = {}

    for row in item_rows:
        if not row.sales_order:
            continue

        sales_orders = (
            sales_orders_by_invoice
            .setdefault(
                row.parent,
                [],
            )
        )

        if (
            row.sales_order
            not in sales_orders
        ):
            sales_orders.append(
                row.sales_order
            )

    sales_order_names = sorted({
        sales_order
        for values
        in sales_orders_by_invoice.values()
        for sales_order in values
    })

    sales_orders = {}

    if sales_order_names:
        for row in frappe.get_all(
            "Sales Order",
            filters={
                "name": [
                    "in",
                    sales_order_names,
                ],
            },
            fields=[
                "name",
                "custom_sector",
                "customer",
            ],
            limit_page_length=0,
        ):
            sales_orders[
                row.name
            ] = row

    trackers_by_sales_order = {}

    if sales_order_names:
        tracker_rows = frappe.get_all(
            "PEPL Document Tracker",
            filters={
                "linked_sales_order": [
                    "in",
                    sales_order_names,
                ],
            },
            fields=[
                "name",
                "linked_sales_order",
                "customer",
                "sector",
                "creation",
            ],
            order_by=(
                "linked_sales_order asc, "
                "creation asc"
            ),
            limit_page_length=0,
        )

        for row in tracker_rows:
            trackers_by_sales_order.setdefault(
                row.linked_sales_order,
                [],
            ).append(row)

    tracker_names = [
        tracker.name
        for values
        in trackers_by_sales_order.values()
        for tracker in values
    ]

    entries_by_tracker = {}

    if tracker_names:
        entries = frappe.get_all(
            "PEPL Document Entry",
            filters={
                "parent": [
                    "in",
                    tracker_names,
                ],
                "parenttype":
                    "PEPL Document Tracker",
                "parentfield":
                    "document_entries",
            },
            fields=[
                "name",
                "parent",
                "document_type",
                "document_status",
                "requirement_code",
                "requirement_source_transaction",
                "source_reference",
                "is_active_requirement",
                "is_historical",
                "idx",
            ],
            order_by=(
                "parent asc, idx asc"
            ),
            limit_page_length=0,
        )

        for entry in entries:
            entries_by_tracker.setdefault(
                entry.parent,
                [],
            ).append(entry)

    requirement_applicability = (
        _get_requirement_applicability()
    )

    data = []

    for invoice in invoices:
        invoice_sales_orders = (
            sales_orders_by_invoice.get(
                invoice.name,
                [],
            )
        )

        if not invoice_sales_orders:
            if filters.get(
                "sales_order"
            ):
                continue

            row = {
                "sales_invoice":
                    invoice.name,
                "posting_date":
                    invoice.posting_date,
                "customer":
                    invoice.customer,
                "sales_order":
                    None,
                "sector":
                    "",
                "document_tracker":
                    None,
                "jcc_status":
                    "No Sales Order",
                "r_note_status":
                    "No Sales Order",
                "i_note_status":
                    "No Sales Order",
                "pending_documents":
                    "",
                "overall_status":
                    "No Sales Order",
                "outstanding_amount":
                    invoice.outstanding_amount,
            }

            if _row_matches_filters(
                row,
                filters,
            ):
                data.append(row)

            continue

        for sales_order_name in (
            invoice_sales_orders
        ):
            if (
                filters.get("sales_order")
                and sales_order_name
                != filters.sales_order
            ):
                continue

            sales_order = (
                sales_orders.get(
                    sales_order_name
                )
            )

            trackers = (
                trackers_by_sales_order.get(
                    sales_order_name,
                    [],
                )
            )

            if not trackers:
                sector = (
                    (
                        sales_order.custom_sector
                        if sales_order
                        else None
                    )
                    or "Others"
                )

                row = _build_report_row(
                    invoice=invoice,
                    sales_order_name=(
                        sales_order_name
                    ),
                    sector=sector,
                    tracker=None,
                    entries=[],
                    requirement_applicability=(
                        requirement_applicability
                    ),
                )

                if _row_matches_filters(
                    row,
                    filters,
                ):
                    data.append(row)

                continue

            for tracker in trackers:
                sector = (
                    tracker.sector
                    or (
                        sales_order.custom_sector
                        if sales_order
                        else None
                    )
                    or "Others"
                )

                row = _build_report_row(
                    invoice=invoice,
                    sales_order_name=(
                        sales_order_name
                    ),
                    sector=sector,
                    tracker=tracker,
                    entries=(
                        entries_by_tracker.get(
                            tracker.name,
                            [],
                        )
                    ),
                    requirement_applicability=(
                        requirement_applicability
                    ),
                )

                if _row_matches_filters(
                    row,
                    filters,
                ):
                    data.append(row)

    return data


def _build_report_row(
    *,
    invoice,
    sales_order_name,
    sector,
    tracker,
    entries,
    requirement_applicability,
):
    statuses = {}

    for key, config in (
        DOCUMENTS.items()
    ):
        statuses[key] = (
            _get_document_status(
                entries=entries,
                invoice_name=invoice.name,
                sector=sector,
                config=config,
                requirement_applicability=(
                    requirement_applicability
                ),
                tracker_exists=bool(
                    tracker
                ),
            )
        )

    pending = []

    for key, config in (
        DOCUMENTS.items()
    ):
        status = statuses[key]

        if status in {
            "Not Applicable",
            "No Sales Order",
        }:
            continue

        if status not in (
            COMPLETED_STATUSES
        ):
            pending.append(
                "{} ({})".format(
                    config["label"],
                    status,
                )
            )

    if not tracker:
        overall_status = (
            "Tracker Missing"
        )
    elif pending:
        overall_status = "Pending"
    else:
        overall_status = "Complete"

    return {
        "sales_invoice":
            invoice.name,
        "posting_date":
            invoice.posting_date,
        "customer":
            invoice.customer,
        "sales_order":
            sales_order_name,
        "sector":
            sector,
        "document_tracker":
            (
                tracker.name
                if tracker
                else None
            ),
        "jcc_status":
            statuses["jcc"],
        "r_note_status":
            statuses["r_note"],
        "i_note_status":
            statuses["i_note"],
        "pending_documents":
            ", ".join(pending),
        "overall_status":
            overall_status,
        "outstanding_amount":
            invoice.outstanding_amount,
    }


def _get_document_status(
    *,
    entries,
    invoice_name,
    sector,
    config,
    requirement_applicability,
    tracker_exists,
):
    if not tracker_exists:
        return "Tracker Missing"

    matching = [
        row
        for row in entries
        if (
            row.requirement_code
            == config["code"]
            or row.document_type
            in config["types"]
        )
        and not row.is_historical
    ]

    if matching:
        invoice_specific = [
            row
            for row in matching
            if (
                row.source_reference
                == invoice_name
            )
        ]

        active = [
            row
            for row in matching
            if row.is_active_requirement
        ]

        candidates = (
            invoice_specific
            or active
            or matching
        )

        return _summarize_statuses(
            candidates
        )

    if _is_applicable(
        config,
        sector,
        requirement_applicability,
    ):
        return "Not Configured"

    return "Not Applicable"


def _summarize_statuses(rows):
    statuses = []

    for row in rows:
        status = (
            row.document_status
            or "Not Set"
        )

        if status not in statuses:
            statuses.append(status)

    if not statuses:
        return "Not Set"

    if len(statuses) == 1:
        return statuses[0]

    incomplete = [
        status
        for status in statuses
        if status
        not in COMPLETED_STATUSES
    ]

    if incomplete:
        return " / ".join(
            incomplete
        )

    return "Received"


def _get_requirement_applicability():
    result = {}

    if not frappe.db.exists(
        "DocType",
        "PEPL Document Requirement",
    ):
        return result

    rows = frappe.get_all(
        "PEPL Document Requirement",
        filters={
            "active": 1,
            "document_code": [
                "in",
                [
                    config["code"]
                    for config
                    in DOCUMENTS.values()
                ],
            ],
        },
        fields=[
            "document_code",
            "sector",
        ],
        limit_page_length=0,
    )

    for row in rows:
        result.setdefault(
            row.document_code,
            set(),
        ).add(
            row.sector
            or "Common"
        )

    return result


def _is_applicable(
    config,
    sector,
    requirement_applicability,
):
    configured_sectors = (
        requirement_applicability.get(
            config["code"]
        )
    )

    if configured_sectors:
        return (
            "Common"
            in configured_sectors
            or sector
            in configured_sectors
        )

    fallback = (
        config[
            "fallback_sector"
        ]
    )

    return (
        fallback == "Common"
        or fallback == sector
    )


def _row_matches_filters(
    row,
    filters,
):
    if (
        filters.get("sector")
        and row.get("sector")
        != filters.sector
    ):
        return False

    if (
        filters.get("overall_status")
        and row.get(
            "overall_status"
        )
        != filters.overall_status
    ):
        return False

    return True


def get_report_summary(data):
    total = len(data)

    pending = sum(
        1
        for row in data
        if row.get(
            "overall_status"
        )
        == "Pending"
    )

    complete = sum(
        1
        for row in data
        if row.get(
            "overall_status"
        )
        == "Complete"
    )

    tracker_missing = sum(
        1
        for row in data
        if row.get(
            "overall_status"
        )
        == "Tracker Missing"
    )

    return [
        {
            "value": total,
            "label": _("Invoices / SO Rows"),
            "datatype": "Int",
        },
        {
            "value": pending,
            "label": _("Pending Documents"),
            "datatype": "Int",
            "indicator": "orange",
        },
        {
            "value": complete,
            "label": _("Document Complete"),
            "datatype": "Int",
            "indicator": "green",
        },
        {
            "value": tracker_missing,
            "label": _("Tracker Missing"),
            "datatype": "Int",
            "indicator": "red",
        },
    ]
