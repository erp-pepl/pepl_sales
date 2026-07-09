import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt, getdate, today


class PEPLCSTCostSheet(Document):
    def autoname(self):
        self.cst_no = make_autoname("CST-.YYYY.-.####")
        self.name = self.cst_no

    def before_save(self):
        if self.linked_item and self.components:
            for comp in self.components:
                self._fetch_reference_rates(comp)

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

        self.total_components_cost = sum(flt(c.component_subtotal) for c in self.components)

        self.overhead_amount = flt(self.total_components_cost) * flt(self.overhead_percent) / 100

        cost_before_profit = (
            flt(self.total_components_cost)
            + flt(self.overhead_amount)
            + flt(self.tender_other_charges)
        )
        self.profit_amount = cost_before_profit * flt(self.profit_percent) / 100

        self.suggested_unit_price = cost_before_profit + flt(self.profit_amount)

        if self.final_bid_price:
            total_cost = (
                flt(self.total_components_cost)
                + flt(self.overhead_amount)
                + flt(self.tender_other_charges)
            )
            self.margin_amount = flt(self.final_bid_price) - total_cost

            if flt(self.final_bid_price) > 0:
                self.margin_percent = (self.margin_amount / flt(self.final_bid_price)) * 100

            if self.margin_amount < 0:
                self.loss_warning = (
                    "<div style=\"background:#ffebee;border-left:4px solid #c62828;"
                    "padding:12px;margin:8px 0;\">"
                    "<strong style=\"color:#c62828;\">&#9888; LOSS-MAKING BID</strong><br>"
                    "Final bid price is below total cost by \u20b9{0}. "
                    "Margin: {1:.1f}%. Verify before submitting."
                    "</div>"
                ).format(abs(flt(self.margin_amount)), flt(self.margin_percent))
            else:
                self.loss_warning = ""
        else:
            self.loss_warning = ""
            self.margin_amount = 0
            self.margin_percent = 0

    def _fetch_reference_rates(self, component):
        """Fetch reference rates for a component from last CST and latest purchase."""
        if not component.component_item:
            return

        last_cst = frappe.db.sql(
            """
            SELECT comp.raw_material_cost + comp.machining_cost +
                   comp.surface_treatment_cost + comp.bought_out_cost +
                   comp.component_other_charges as last_rate
            FROM `tabPEPL CST Component` comp
            INNER JOIN `tabPEPL CST Cost Sheet` cst ON comp.parent = cst.name
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
            INNER JOIN `tabPurchase Receipt` parent ON pr.parent = parent.name
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

    product = frappe.get_doc("PEPL Product Master", cst.linked_product)

    if not product.assembly_components:
        if product.product_type == "Single Component" and product.linked_item:
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
        else:
            frappe.throw(
                _("Product has no assembly components and is not a single-component product")
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


@frappe.whitelist()
def fetch_competitor_history(cst_name):
    """Fetch competitor data from past tenders for this product/item."""

    cst = frappe.get_doc("PEPL CST Cost Sheet", cst_name)

    if not cst.linked_item:
        return {"added": 0, "message": "No linked item to search"}

    competitors = frappe.db.sql(
        """
        SELECT
            t.name as tender_ref,
            t.publication_date as tender_date,
            tc.competitor_name,
            tc.competitor_price,
            tc.rank,
            ti.our_rank,
            ti.outcome
        FROM `tabPEPL Tender Item Competitor` tc
        INNER JOIN `tabPEPL Tender Item` ti ON tc.parent = ti.name
        INNER JOIN `tabPEPL Tender` t ON ti.parent = t.name
        WHERE ti.item = %s
          AND t.status IN ('Won', 'Lost', 'Partially Won')
        ORDER BY t.publication_date DESC
        LIMIT 50
        """,
        cst.linked_item,
        as_dict=True,
    )

    cst.competitors = []

    for c in competitors:
        cst.append(
            "competitors",
            {
                "tender_reference": c.tender_ref,
                "tender_date": c.tender_date,
                "competitor_name": c.competitor_name,
                "competitor_price": c.competitor_price,
                "rank": c.rank,
                "our_rank": c.our_rank,
                "outcome": c.outcome,
            },
        )

    cst.save()
    return {"added": len(competitors)}
