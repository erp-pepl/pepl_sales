import frappe
from frappe import _
from frappe.utils import flt


FINAL_STATUSES = [
    "Won",
    "Partially Won",
    "Lost",
    "Cancelled",
    "No Bid",
    "Re-tendered",
]


def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    data = get_data(filters)
    summary = get_report_summary(data)

    return columns, data, None, None, summary


def get_columns():
    return [
        {
            "label": _("Tender"),
            "fieldname": "tender",
            "fieldtype": "Link",
            "options": "PEPL Tender",
            "width": 150,
        },
        {
            "label": _("Tender Reference"),
            "fieldname": "nit_number",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Tender Title"),
            "fieldname": "tender_title",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": _("Publication Date"),
            "fieldname": "publication_date",
            "fieldtype": "Date",
            "width": 105,
        },
        {
            "label": _("Outcome Date"),
            "fieldname": "outcome_date",
            "fieldtype": "Date",
            "width": 105,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 180,
        },
        {
            "label": _("Sector"),
            "fieldname": "sector",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Items"),
            "fieldname": "item_count",
            "fieldtype": "Int",
            "width": 75,
        },
        {
            "label": _("Items Won / Partial"),
            "fieldname": "items_won",
            "fieldtype": "Int",
            "width": 125,
        },
        {
            "label": _("Items Lost"),
            "fieldname": "items_lost",
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "label": _("Win Rate %"),
            "fieldname": "win_rate",
            "fieldtype": "Percent",
            "width": 90,
        },
        {
            "label": _("Estimated Value"),
            "fieldname": "total_estimated_value",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Our Bid Value"),
            "fieldname": "total_bid_value",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Winning Value"),
            "fieldname": "winning_price",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("PEPL Rank"),
            "fieldname": "our_overall_rank",
            "fieldtype": "Data",
            "width": 95,
        },
        {
            "label": _("Winning Competitor"),
            "fieldname": "winning_competitor",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Win Reason"),
            "fieldname": "win_reason",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Loss Category"),
            "fieldname": "loss_reason",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Detailed Loss Reason"),
            "fieldname": "detailed_loss_reason",
            "fieldtype": "Data",
            "width": 240,
        },
        {
            "label": _("Corrective Action"),
            "fieldname": "corrective_action",
            "fieldtype": "Data",
            "width": 240,
        },
        {
            "label": _("Result Attachment"),
            "fieldname": "financial_result_attachment",
            "fieldtype": "Attach",
            "width": 140,
        },
        {
            "label": _("Analysis Finalised"),
            "fieldname": "competitor_analysis_completed",
            "fieldtype": "Check",
            "width": 115,
        },
        {
            "label": _("Sales Order"),
            "fieldname": "linked_sales_order",
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 140,
        },
    ]


def get_data(filters):
    tender_filters = {}

    if filters.get("from_date") and filters.get("to_date"):
        tender_filters["outcome_date"] = [
            "between",
            [filters.from_date, filters.to_date],
        ]
    elif filters.get("from_date"):
        tender_filters["outcome_date"] = [">=", filters.from_date]
    elif filters.get("to_date"):
        tender_filters["outcome_date"] = ["<=", filters.to_date]

    if filters.get("customer"):
        tender_filters["customer"] = filters.customer

    if filters.get("sector"):
        tender_filters["sector"] = filters.sector

    if filters.get("status"):
        tender_filters["status"] = filters.status

    if filters.get("loss_reason"):
        tender_filters["loss_reason"] = filters.loss_reason

    tenders = frappe.get_all(
        "PEPL Tender",
        filters=tender_filters,
        fields=[
            "name",
            "nit_number",
            "tender_title",
            "publication_date",
            "outcome_date",
            "customer",
            "sector",
            "status",
            "items_won",
            "items_lost",
            "win_rate",
            "total_estimated_value",
            "total_bid_value",
            "winning_price",
            "our_overall_rank",
            "winning_competitor",
            "win_reason",
            "loss_reason",
            "detailed_loss_reason",
            "corrective_action",
            "financial_result_attachment",
            "competitor_analysis_completed",
            "linked_sales_order",
        ],
        order_by="outcome_date desc, modified desc",
        limit_page_length=0,
    )

    if not tenders:
        return []

    tender_names = [row.name for row in tenders]

    item_filters = {
        "parent": ["in", tender_names],
        "parenttype": "PEPL Tender",
    }

    if filters.get("item"):
        item_filters["item"] = filters.item

    tender_items = frappe.get_all(
        "PEPL Tender Item",
        filters=item_filters,
        fields=[
            "name",
            "parent",
            "item",
            "outcome",
            "item_loss_category",
        ],
        limit_page_length=0,
    )

    items_by_tender = {}

    for row in tender_items:
        items_by_tender.setdefault(row.parent, []).append(row)

    matching_tenders = set(tender_names)

    if filters.get("item"):
        matching_tenders = {
            row.parent
            for row in tender_items
            if row.item == filters.item
        }

    if filters.get("competitor"):
        item_names = [row.name for row in tender_items]

        if not item_names:
            return []

        competitor_rows = frappe.get_all(
            "PEPL Tender Item Competitor",
            filters={
                "parent": ["in", item_names],
                "parenttype": "PEPL Tender Item",
                "competitor_name": ["like", f"%{filters.competitor}%"],
            },
            fields=["parent", "competitor_name"],
            limit_page_length=0,
        )

        matching_item_names = {
            row.parent
            for row in competitor_rows
        }

        competitor_tenders = {
            row.parent
            for row in tender_items
            if row.name in matching_item_names
        }

        matching_tenders = matching_tenders.intersection(
            competitor_tenders
        )

    data = []

    for tender in tenders:
        if tender.name not in matching_tenders:
            continue

        item_rows = items_by_tender.get(tender.name, [])

        data.append(
            {
                "tender": tender.name,
                "nit_number": tender.nit_number,
                "tender_title": tender.tender_title,
                "publication_date": tender.publication_date,
                "outcome_date": tender.outcome_date,
                "customer": tender.customer,
                "sector": tender.sector,
                "status": tender.status,
                "item_count": len(item_rows),
                "items_won": tender.items_won,
                "items_lost": tender.items_lost,
                "win_rate": tender.win_rate,
                "total_estimated_value": tender.total_estimated_value,
                "total_bid_value": tender.total_bid_value,
                "winning_price": tender.winning_price,
                "our_overall_rank": tender.our_overall_rank,
                "winning_competitor": tender.winning_competitor,
                "win_reason": tender.win_reason,
                "loss_reason": tender.loss_reason,
                "detailed_loss_reason": tender.detailed_loss_reason,
                "corrective_action": tender.corrective_action,
                "financial_result_attachment":
                    tender.financial_result_attachment,
                "competitor_analysis_completed":
                    tender.competitor_analysis_completed,
                "linked_sales_order": tender.linked_sales_order,
            }
        )

    return data


def get_report_summary(data):
    total_tenders = len(data)

    won = sum(
        1
        for row in data
        if row.get("status") == "Won"
    )

    partial = sum(
        1
        for row in data
        if row.get("status") == "Partially Won"
    )

    lost = sum(
        1
        for row in data
        if row.get("status") == "Lost"
    )

    total_bid = sum(
        flt(row.get("total_bid_value"))
        for row in data
    )

    total_winning = sum(
        flt(row.get("winning_price"))
        for row in data
    )

    success_rate = (
        ((won + partial) / total_tenders) * 100
        if total_tenders
        else 0
    )

    return [
        {
            "value": total_tenders,
            "label": _("Total Tenders"),
            "datatype": "Int",
        },
        {
            "value": won,
            "label": _("Won"),
            "datatype": "Int",
            "indicator": "Green",
        },
        {
            "value": partial,
            "label": _("Partially Won"),
            "datatype": "Int",
            "indicator": "Blue",
        },
        {
            "value": lost,
            "label": _("Lost"),
            "datatype": "Int",
            "indicator": "Red",
        },
        {
            "value": success_rate,
            "label": _("Success Rate"),
            "datatype": "Percent",
        },
        {
            "value": total_bid,
            "label": _("Total Bid Value"),
            "datatype": "Currency",
        },
        {
            "value": total_winning,
            "label": _("Winning Value"),
            "datatype": "Currency",
        },
    ]
