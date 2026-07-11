import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, today


FINAL_TENDER_STATUSES = ("Won", "Lost", "Partially Won")


class PEPLCSTCostSheet(Document):
    def autoname(self):
        self.cst_no = make_autoname("CST-.YYYY.-.####")
        self.name = self.cst_no

    def before_save(self):
        if self.linked_item and self.components:
            for comp in self.components:
                self._fetch_reference_rates(comp)

    def on_update(self):
        self.link_cost_sheet_to_tender()

    def link_cost_sheet_to_tender(self):
        """Link this Cost Sheet to its specific Tender Item row."""
        if not self.linked_tender:
            return

        tender = frappe.get_doc("PEPL Tender", self.linked_tender)
        linked_row = None

        if self.linked_tender_item:
            linked_row = next(
                (
                    row
                    for row in tender.items or []
                    if row.name == self.linked_tender_item
                ),
                None,
            )

        if not linked_row and self.linked_item:
            linked_row = next(
                (
                    row
                    for row in tender.items or []
                    if row.item == self.linked_item
                ),
                None,
            )

        if linked_row and linked_row.linked_cost_sheet != self.name:
            linked_row.linked_cost_sheet = self.name

        status_field = tender.meta.get_field("status")

        if status_field and status_field.options:
            allowed_statuses = [
                option.strip()
                for option in status_field.options.splitlines()
                if option.strip()
            ]

            if (
                "Costed" in allowed_statuses
                and tender.status in {"Draft", "Active Bid", "Costing"}
            ):
                tender.status = "Costed"

        tender.save(ignore_permissions=True)

    def validate(self):
        for comp in self.components:
            if comp.manufactured_or_bought_out == "Manufactured":
                comp.component_subtotal = (
                    flt(comp.raw_material_cost)
                    + flt(comp.machining_cost)
                    + flt(comp.surface_treatment_cost)
                    + flt(comp.component_other_charges)
                )
            elif comp.manufactured_or_bought_out == "Bought Out":
                comp.component_subtotal = (
                    flt(comp.bought_out_cost)
                    + flt(comp.surface_treatment_cost)
                    + flt(comp.component_other_charges)
                )

        self.total_components_cost = sum(
            flt(c.component_subtotal)
            for c in self.components
        )

        self.overhead_amount = (
            flt(self.total_components_cost)
            * flt(self.overhead_percent)
            / 100
        )

        cost_before_profit = (
            flt(self.total_components_cost)
            + flt(self.overhead_amount)
            + flt(self.tender_other_charges)
        )
        self.profit_amount = (
            cost_before_profit
            * flt(self.profit_percent)
            / 100
        )

        self.suggested_unit_price = (
            cost_before_profit
            + flt(self.profit_amount)
        )

        if self.final_bid_price:
            total_cost = (
                flt(self.total_components_cost)
                + flt(self.overhead_amount)
                + flt(self.tender_other_charges)
            )
            self.margin_amount = (
                flt(self.final_bid_price)
                - total_cost
            )

            if flt(self.final_bid_price) > 0:
                self.margin_percent = (
                    self.margin_amount
                    / flt(self.final_bid_price)
                ) * 100

            if self.margin_amount < 0:
                self.loss_warning = (
                    "<div style=\"background:#ffebee;"
                    "border-left:4px solid #c62828;"
                    "padding:12px;margin:8px 0;\">"
                    "<strong style=\"color:#c62828;\">"
                    "&#9888; LOSS-MAKING BID</strong><br>"
                    "Final bid price is below total cost by ₹{0}. "
                    "Margin: {1:.1f}%. Verify before submitting."
                    "</div>"
                ).format(
                    abs(flt(self.margin_amount)),
                    flt(self.margin_percent),
                )
            else:
                self.loss_warning = ""
        else:
            self.loss_warning = ""
            self.margin_amount = 0
            self.margin_percent = 0

    def _fetch_reference_rates(self, component):
        """Fetch reference rates for a component from last CST and purchase."""
        if not component.component_item:
            return

        last_cst = frappe.db.sql(
            """
            SELECT comp.raw_material_cost + comp.machining_cost +
                   comp.surface_treatment_cost + comp.bought_out_cost +
                   comp.component_other_charges as last_rate
            FROM `tabPEPL CST Component` comp
            INNER JOIN `tabPEPL CST Cost Sheet` cst
                ON comp.parent = cst.name
            WHERE comp.component_item = %s
              AND cst.name != %s
              AND cst.status IN ('Approved', 'Used in Bid')
            ORDER BY cst.costing_date DESC
            LIMIT 1
            """,
            (component.component_item, self.name or ""),
            as_dict=True,
        )
        if last_cst:
            component.reference_rate_last_cst = last_cst[0].last_rate

        latest_purchase = frappe.db.sql(
            """
            SELECT pr.rate
            FROM `tabPurchase Receipt Item` pr
            INNER JOIN `tabPurchase Receipt` parent
                ON pr.parent = parent.name
            WHERE pr.item_code = %s
              AND parent.docstatus = 1
            ORDER BY parent.posting_date DESC
            LIMIT 1
            """,
            component.component_item,
            as_dict=True,
        )
        if latest_purchase:
            component.reference_rate_purchase = latest_purchase[0].rate


@frappe.whitelist()
def sync_components_from_product(cst_name):
    """Sync components from linked PEPL Product Master."""
    cst = frappe.get_doc("PEPL CST Cost Sheet", cst_name)

    if not cst.linked_product:
        frappe.throw(_("Set Linked Product first"))

    product = frappe.get_doc(
        "PEPL Product Master",
        cst.linked_product,
    )

    if not product.assembly_components:
        if (
            product.product_type == "Single Component"
            and product.linked_item
        ):
            cst.components = []
            cst.append(
                "components",
                {
                    "manufactured_or_bought_out": "Manufactured",
                    "component_item": product.linked_item,
                    "quantity_per_assembly": 1,
                    "uom": "Nos",
                },
            )
            cst.save()
            return {"synced": 1}

        frappe.throw(
            _(
                "Product has no assembly components and is not "
                "a single-component product"
            )
        )

    cst.components = []

    for comp in product.assembly_components:
        new_row = {
            "manufactured_or_bought_out": "Manufactured",
            "quantity_per_assembly": comp.quantity,
            "uom": comp.uom or "Nos",
            "component_drawing_no": comp.component_drawing_no,
        }

        if comp.component_item:
            new_row["component_item"] = comp.component_item

        if comp.component_product:
            new_row["component_product"] = comp.component_product

        cst.append("components", new_row)

    cst.save()
    return {"synced": len(product.assembly_components)}


def _get_matching_tenders(cst):
    """Return the first non-empty priority tier of historical Tenders."""
    priorities = []

    if cst.customer and cst.sector:
        priorities.append(
            (
                "Customer + Sector + Item",
                {
                    "customer": cst.customer,
                    "sector": cst.sector,
                    "status": ["in", FINAL_TENDER_STATUSES],
                },
            )
        )

    if cst.sector:
        priorities.append(
            (
                "Sector + Item",
                {
                    "sector": cst.sector,
                    "status": ["in", FINAL_TENDER_STATUSES],
                },
            )
        )

    priorities.append(
        (
            "Item",
            {
                "status": ["in", FINAL_TENDER_STATUSES],
            },
        )
    )

    for match_level, filters in priorities:
        tenders = frappe.get_all(
            "PEPL Tender",
            filters=filters,
            fields=[
                "name",
                "publication_date",
                "customer",
                "sector",
                "result_source_type",
                "status",
            ],
            order_by="publication_date desc, modified desc",
            limit_page_length=200,
        )

        matched = []

        for tender in tenders:
            item_rows = frappe.get_all(
                "PEPL Tender Item",
                filters={
                    "parent": tender.name,
                    "parenttype": "PEPL Tender",
                    "item": cst.linked_item,
                    "outcome": [
                        "in",
                        (
                            "Won",
                            "Partially Won",
                            "Lost",
                            "Cancelled",
                        ),
                    ],
                },
                fields=[
                    "name",
                    "item",
                    "evaluation_basis",
                    "our_rank",
                    "outcome",
                    "winning_price",
                ],
                order_by="idx asc",
                limit_page_length=0,
            )

            for item_row in item_rows:
                matched.append((tender, item_row))

        if matched:
            return match_level, matched

    return "None", []


def _group_competitor_rows(rows):
    """Group competitor rows by consignee for price comparisons."""
    groups = {}

    for row in rows:
        key = (row.consignee or "").strip() or "__DEFAULT__"
        groups.setdefault(key, []).append(row)

    return groups


def _get_group_reference_prices(rows):
    """Return PEPL and winner prices for a consignee group."""
    priced_rows = [
        row
        for row in rows
        if flt(row.competitor_price) > 0
    ]

    pepl_rows = [
        row
        for row in priced_rows
        if row.is_pepl
    ]
    pepl_price = min(
        [flt(row.competitor_price) for row in pepl_rows]
        or [0]
    )

    winner_rows = [
        row
        for row in priced_rows
        if row.is_winner or row.buyer_selected
    ]

    if not winner_rows:
        winner_rows = [
            row
            for row in priced_rows
            if row.is_l1 or flt(row.rank_number) == 1
        ]

    if not winner_rows and priced_rows:
        winner_rows = [
            min(
                priced_rows,
                key=lambda row: flt(row.competitor_price),
            )
        ]

    winning_price = min(
        [flt(row.competitor_price) for row in winner_rows]
        or [0]
    )

    return pepl_price, winning_price


@frappe.whitelist()
def fetch_competitor_history(cst_name):
    """Fetch structured historical competitor data into a Cost Sheet.

    Matching priority:
    1. Customer + Sector + Item
    2. Sector + Item
    3. Item

    Repeated execution is idempotent because rows are rebuilt with a
    deterministic history_key.
    """
    cst = frappe.get_doc("PEPL CST Cost Sheet", cst_name)

    if not cst.linked_item:
        return {
            "added": 0,
            "match_level": "None",
            "message": "No linked item to search",
        }

    match_level, tender_item_pairs = _get_matching_tenders(cst)

    history_rows = []
    seen_keys = set()

    for tender, item_row in tender_item_pairs:
        competitor_rows = frappe.get_all(
            "PEPL Tender Item Competitor",
            filters={
                "parent": item_row.name,
                "parenttype": "PEPL Tender Item",
            },
            fields=[
                "name",
                "competitor_name",
                "competitor_price",
                "rank",
                "rank_number",
                "is_pepl",
                "is_l1",
                "is_winner",
                "buyer_selected",
                "consignee",
                "evaluation_basis",
                "bid_id",
                "bid_datetime",
                "basic_rate",
                "gst_percent",
                "evaluated_unit_rate",
                "total_bid_value",
                "difference_from_pepl",
                "difference_from_pepl_percent",
                "is_msme",
                "is_mii",
                "award_share_percent",
                "awarded_quantity",
                "remarks",
            ],
            order_by="idx asc",
            limit_page_length=0,
        )

        groups = _group_competitor_rows(competitor_rows)
        group_prices = {}

        for group_key, rows in groups.items():
            group_prices[group_key] = _get_group_reference_prices(rows)

        for row in competitor_rows:
            consignee_key = (
                (row.consignee or "").strip()
                or "__DEFAULT__"
            )
            pepl_price, winning_price = group_prices.get(
                consignee_key,
                (0, 0),
            )

            history_key = "|".join(
                [
                    tender.name,
                    item_row.name,
                    row.name,
                    consignee_key,
                ]
            )

            if history_key in seen_keys:
                continue

            seen_keys.add(history_key)

            history_rows.append(
                {
                    "tender_reference": tender.name,
                    "tender_date": tender.publication_date,
                    "customer": tender.customer,
                    "sector": tender.sector,
                    "item": item_row.item,
                    "consignee": row.consignee,
                    "evaluation_basis": (
                        row.evaluation_basis
                        or item_row.evaluation_basis
                    ),
                    "result_source_type": tender.result_source_type,
                    "source_bid_id": row.bid_id,
                    "source_bid_datetime": row.bid_datetime,
                    "competitor_name": row.competitor_name,
                    "competitor_price": row.competitor_price,
                    "rank": row.rank,
                    "our_rank": item_row.our_rank,
                    "outcome": (
                        item_row.outcome
                        if item_row.outcome
                        in {
                            "Won",
                            "Partially Won",
                            "Lost",
                            "Cancelled",
                        }
                        else "Unknown"
                    ),
                    "basic_rate": row.basic_rate,
                    "gst_percent": row.gst_percent,
                    "evaluated_unit_rate": row.evaluated_unit_rate,
                    "total_bid_value": row.total_bid_value,
                    "pepl_price": pepl_price,
                    "winning_price": winning_price,
                    "difference_from_pepl": row.difference_from_pepl,
                    "difference_from_pepl_percent": (
                        row.difference_from_pepl_percent
                    ),
                    "is_pepl": row.is_pepl,
                    "is_l1": row.is_l1,
                    "is_winner": row.is_winner,
                    "buyer_selected": row.buyer_selected,
                    "is_msme": row.is_msme,
                    "is_mii": row.is_mii,
                    "award_share_percent": row.award_share_percent,
                    "awarded_quantity": row.awarded_quantity,
                    "remarks": row.remarks,
                    "history_key": history_key,
                }
            )

    history_rows.sort(
        key=lambda row: (
            str(row.get("tender_date") or ""),
            row.get("tender_reference") or "",
            row.get("consignee") or "",
            flt(row.get("competitor_price")),
        ),
        reverse=True,
    )

    cst.set("competitors", [])

    for row in history_rows[:200]:
        cst.append("competitors", row)

    cst.save(ignore_permissions=True)

    return {
        "added": min(len(history_rows), 200),
        "match_level": match_level,
        "total_found": len(history_rows),
        "message": (
            "Loaded competitor history using {0} matching."
        ).format(match_level),
    }


@frappe.whitelist()
def clone_cost_sheet_for_new_tender(
    cst_name,
    new_tender,
    tender_item=None,
):
    """Clone an existing CST Cost Sheet for another Tender."""
    if not cst_name:
        frappe.throw(_("Source Cost Sheet is required."))

    if not new_tender:
        frappe.throw(_("New Tender is required."))

    source_cst = frappe.get_doc("PEPL CST Cost Sheet", cst_name)
    tender = frappe.get_doc("PEPL Tender", new_tender)

    selected_tender_item = None

    if tender_item:
        for row in tender.items or []:
            if row.name == tender_item:
                selected_tender_item = row
                break

        if not selected_tender_item:
            frappe.throw(
                _(
                    "The selected Tender Item does not belong "
                    "to Tender {0}."
                ).format(new_tender)
            )

    elif tender.items:
        selected_tender_item = tender.items[0]

    new_cst = frappe.copy_doc(source_cst)

    new_cst.linked_tender = tender.name
    new_cst.customer = tender.customer
    new_cst.sector = tender.sector
    new_cst.status = "Draft"
    new_cst.costing_date = today()

    new_cst.prepared_by = frappe.session.user
    new_cst.approved_by = None
    new_cst.approved_date = None
    new_cst.valid_until = None

    new_cst.final_bid_price = 0
    new_cst.margin_amount = 0
    new_cst.margin_percent = 0
    new_cst.loss_warning = ""

    new_cst.set("competitors", [])

    if selected_tender_item:
        new_cst.linked_tender_item = selected_tender_item.name
        new_cst.linked_item = selected_tender_item.item

        item_label = selected_tender_item.item or "Item"

        if selected_tender_item.item:
            item_label = (
                frappe.db.get_value(
                    "Item",
                    selected_tender_item.item,
                    "item_name",
                )
                or selected_tender_item.item
            )

        new_cst.cst_title = "{0} - {1}".format(
            tender.tender_title or tender.name,
            item_label,
        )
    else:
        new_cst.linked_tender_item = None
        new_cst.linked_item = None
        new_cst.cst_title = "{} - Cloned Cost Sheet".format(
            tender.tender_title or tender.name
        )

    new_cst.insert(ignore_permissions=True)

    return {
        "created": True,
        "cost_sheet": new_cst.name,
        "tender": tender.name,
        "linked_item": new_cst.linked_item,
    }
