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
            "label": _("Tender"),
            "fieldname": "tender",
            "fieldtype": "Link",
            "options": "PEPL Tender",
            "width": 145,
        },
        {
            "label": _("NIT / Reference"),
            "fieldname": "nit_number",
            "fieldtype": "Data",
            "width": 145,
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
            "width": 175,
        },
        {
            "label": _("Sector"),
            "fieldname": "sector",
            "fieldtype": "Data",
            "width": 95,
        },
        {
            "label": _("Item"),
            "fieldname": "item",
            "fieldtype": "Link",
            "options": "Item",
            "width": 145,
        },
        {
            "label": _("Item Outcome"),
            "fieldname": "item_outcome",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Consignee"),
            "fieldname": "consignee",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Competitor"),
            "fieldname": "competitor_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("PEPL"),
            "fieldname": "is_pepl",
            "fieldtype": "Check",
            "width": 60,
        },
        {
            "label": _("Evaluation Basis"),
            "fieldname": "evaluation_basis",
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "label": _("Technical Status"),
            "fieldname": "technical_status",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": _("Commercial Status"),
            "fieldname": "commercial_status",
            "fieldtype": "Data",
            "width": 125,
        },
        {
            "label": _("Calculated Unit Rate"),
            "fieldname": "calculated_unit_rate",
            "fieldtype": "Currency",
            "width": 135,
        },
        {
            "label": _("Evaluated Unit Rate"),
            "fieldname": "evaluated_unit_rate",
            "fieldtype": "Currency",
            "width": 135,
        },
        {
            "label": _("Total Bid Value"),
            "fieldname": "total_bid_value",
            "fieldtype": "Currency",
            "width": 125,
        },
        {
            "label": _("Primary Price"),
            "fieldname": "competitor_price",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": _("Rank"),
            "fieldname": "rank",
            "fieldtype": "Data",
            "width": 70,
        },
        {
            "label": _("Rank Number"),
            "fieldname": "rank_number",
            "fieldtype": "Int",
            "width": 90,
        },
        {
            "label": _("L1"),
            "fieldname": "is_l1",
            "fieldtype": "Check",
            "width": 55,
        },
        {
            "label": _("Winner"),
            "fieldname": "is_winner",
            "fieldtype": "Check",
            "width": 65,
        },
        {
            "label": _("Buyer Selected"),
            "fieldname": "buyer_selected",
            "fieldtype": "Check",
            "width": 95,
        },
        {
            "label": _("Awarded Quantity"),
            "fieldname": "awarded_quantity",
            "fieldtype": "Float",
            "width": 115,
        },
        {
            "label": _("Award Share %"),
            "fieldname": "award_share_percent",
            "fieldtype": "Percent",
            "width": 105,
        },
        {
            "label": _("Awarded Value"),
            "fieldname": "awarded_value",
            "fieldtype": "Currency",
            "width": 115,
        },
        {
            "label": _("Difference from PEPL"),
            "fieldname": "difference_from_pepl",
            "fieldtype": "Currency",
            "width": 135,
        },
        {
            "label": _("Difference from PEPL %"),
            "fieldname": "difference_from_pepl_percent",
            "fieldtype": "Percent",
            "width": 145,
        },
        {
            "label": _("Difference from L1"),
            "fieldname": "difference_from_l1",
            "fieldtype": "Currency",
            "width": 125,
        },
        {
            "label": _("Difference from L1 %"),
            "fieldname": "difference_from_l1_percent",
            "fieldtype": "Percent",
            "width": 135,
        },
        {
            "label": _("MSE / MSME"),
            "fieldname": "is_msme",
            "fieldtype": "Check",
            "width": 85,
        },
        {
            "label": _("MII"),
            "fieldname": "is_mii",
            "fieldtype": "Check",
            "width": 55,
        },
        {
            "label": _("Bid Date / Time"),
            "fieldname": "bid_datetime",
            "fieldtype": "Datetime",
            "width": 145,
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

    if filters.get("tender"):
        tender_filters["name"] = filters.tender

    if filters.get("customer"):
        tender_filters["customer"] = filters.customer

    if filters.get("sector"):
        tender_filters["sector"] = filters.sector

    tenders = frappe.get_all(
        "PEPL Tender",
        filters=tender_filters,
        fields=[
            "name",
            "nit_number",
            "outcome_date",
            "customer",
            "sector",
            "status",
        ],
        order_by="outcome_date desc, modified desc",
        limit_page_length=0,
    )

    if not tenders:
        return []

    tender_map = {
        row.name: row
        for row in tenders
    }

    item_filters = {
        "parent": ["in", list(tender_map)],
        "parenttype": "PEPL Tender",
    }

    if filters.get("item"):
        item_filters["item"] = filters.item

    if filters.get("item_outcome"):
        item_filters["outcome"] = filters.item_outcome

    items = frappe.get_all(
        "PEPL Tender Item",
        filters=item_filters,
        fields=[
            "name",
            "parent",
            "item",
            "outcome",
            "quantity",
            "uom",
        ],
        limit_page_length=0,
    )

    if not items:
        return []

    item_map = {
        row.name: row
        for row in items
    }

    competitor_filters = {
        "parent": ["in", list(item_map)],
        "parenttype": "PEPL Tender Item",
    }

    if filters.get("competitor"):
        competitor_filters["competitor_name"] = [
            "like",
            f"%{filters.competitor}%",
        ]

    if filters.get("is_pepl") not in (None, ""):
        competitor_filters["is_pepl"] = int(filters.is_pepl)

    if filters.get("rank"):
        competitor_filters["rank"] = filters.rank

    if filters.get("winner_only"):
        competitor_filters["is_winner"] = 1

    competitors = frappe.get_all(
        "PEPL Tender Item Competitor",
        filters=competitor_filters,
        fields=[
            "name",
            "parent",
            "competitor_name",
            "is_pepl",
            "bid_id",
            "bid_datetime",
            "rank",
            "rank_number",
            "is_l1",
            "is_winner",
            "buyer_selected",
            "consignee",
            "evaluation_basis",
            "technical_status",
            "commercial_status",
            "calculated_unit_rate",
            "evaluated_unit_rate",
            "total_bid_value",
            "competitor_price",
            "award_share_percent",
            "awarded_quantity",
            "awarded_value",
            "difference_from_pepl",
            "difference_from_pepl_percent",
            "difference_from_l1",
            "difference_from_l1_percent",
            "is_msme",
            "is_mii",
        ],
        order_by="parent asc, competitor_price asc",
        limit_page_length=0,
    )

    data = []

    for competitor in competitors:
        item = item_map.get(competitor.parent)

        if not item:
            continue

        tender = tender_map.get(item.parent)

        if not tender:
            continue

        data.append(
            {
                "tender": tender.name,
                "nit_number": tender.nit_number,
                "outcome_date": tender.outcome_date,
                "customer": tender.customer,
                "sector": tender.sector,
                "item": item.item,
                "item_outcome": item.outcome,
                "consignee": competitor.consignee,
                "competitor_name": competitor.competitor_name,
                "is_pepl": competitor.is_pepl,
                "evaluation_basis": competitor.evaluation_basis,
                "technical_status": competitor.technical_status,
                "commercial_status": competitor.commercial_status,
                "calculated_unit_rate":
                    competitor.calculated_unit_rate,
                "evaluated_unit_rate":
                    competitor.evaluated_unit_rate,
                "total_bid_value": competitor.total_bid_value,
                "competitor_price": competitor.competitor_price,
                "rank": competitor.rank,
                "rank_number": competitor.rank_number,
                "is_l1": competitor.is_l1,
                "is_winner": competitor.is_winner,
                "buyer_selected": competitor.buyer_selected,
                "awarded_quantity": competitor.awarded_quantity,
                "award_share_percent":
                    competitor.award_share_percent,
                "awarded_value": competitor.awarded_value,
                "difference_from_pepl":
                    competitor.difference_from_pepl,
                "difference_from_pepl_percent":
                    competitor.difference_from_pepl_percent,
                "difference_from_l1":
                    competitor.difference_from_l1,
                "difference_from_l1_percent":
                    competitor.difference_from_l1_percent,
                "is_msme": competitor.is_msme,
                "is_mii": competitor.is_mii,
                "bid_datetime": competitor.bid_datetime,
            }
        )

    return data


def get_report_summary(data):
    bidder_rows = len(data)

    unique_tenders = {
        row.get("tender")
        for row in data
        if row.get("tender")
    }

    unique_competitors = {
        row.get("competitor_name")
        for row in data
        if row.get("competitor_name")
    }

    pepl_rows = sum(
        1
        for row in data
        if row.get("is_pepl")
    )

    l1_rows = sum(
        1
        for row in data
        if row.get("is_l1")
    )

    winner_rows = sum(
        1
        for row in data
        if row.get("is_winner") or row.get("buyer_selected")
    )

    awarded_value = sum(
        flt(row.get("awarded_value"))
        for row in data
    )

    return [
        {
            "value": len(unique_tenders),
            "label": _("Tenders"),
            "datatype": "Int",
        },
        {
            "value": bidder_rows,
            "label": _("Bidder Rows"),
            "datatype": "Int",
        },
        {
            "value": len(unique_competitors),
            "label": _("Competitors"),
            "datatype": "Int",
        },
        {
            "value": pepl_rows,
            "label": _("PEPL Rows"),
            "datatype": "Int",
        },
        {
            "value": l1_rows,
            "label": _("L1 Rows"),
            "datatype": "Int",
        },
        {
            "value": winner_rows,
            "label": _("Winner Rows"),
            "datatype": "Int",
        },
        {
            "value": awarded_value,
            "label": _("Awarded Value"),
            "datatype": "Currency",
        },
    ]
