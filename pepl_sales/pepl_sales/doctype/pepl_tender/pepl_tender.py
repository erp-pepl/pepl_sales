import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, flt, add_days


class PEPLTender(Document):
    def autoname(self):
        from frappe.model.naming import make_autoname
        self.tender_no = make_autoname("TND-.YYYY.-.####")
        self.name = self.tender_no

    def validate(self):
        # Auto-set sub-sector from customer group if not already set
        if self.customer_group and not self.sub_sector:
            cg = self.customer_group
            mapping = {
                "Railways - Loco": "Railways - Loco",
                "Railways - Coaches": "Railways - Coaches",
                "Railways - Zonal": "Railways - Zonal",
                "Defence - MIL": "Defence - MIL",
                "Defence - YIL": "Defence - YIL",
                "Defence - AWEIL": "Defence - AWEIL",
                "Defence - Private": "Defence - Private",
                "Private Sector": "Private Sector",
                "PSU": "PSU"
            }
            if cg in mapping:
                self.sub_sector = mapping[cg]

        # Auto-set sector from customer group
        if self.customer_group and not self.sector:
            if "Railways" in self.customer_group:
                self.sector = "Railways"
            elif "Defence" in self.customer_group:
                self.sector = "Defence"
            elif "Private" in self.customer_group:
                self.sector = "Private"
            else:
                self.sector = "Others"

        # Auto-fetch vendor approval stage and drawing/spec for each item
        if self.items:
            for item_row in self.items:
                if item_row.item and self.sector:
                    self._fetch_item_details(item_row)

        # Calculate summary fields
        self._calculate_summary()

        # Auto-update overall status based on item outcomes
        self._update_overall_status()

        # Process PO Schedule: recalc totals, flag won-list status, sum parent total
        self._process_po_schedule()

        # Validation: bid deadline check
        if self.bid_submission_deadline and self.is_new():
            if getdate(self.bid_submission_deadline) < getdate(today()):
                frappe.msgprint(
                    _("Bid deadline {0} is in the past — please verify").format(
                        self.bid_submission_deadline
                    ),
                    indicator="orange",
                    alert=True
                )

    def _fetch_item_details(self, item_row):
        """Fetch drawing, spec, vendor approval stage, PL number for an item row.
        Uses frappe.db.has_column to check field existence before query —
        bypasses field-level permission errors on custom fields."""

        if item_row.item:
            has_pl = frappe.db.has_column("Item", "custom_pl_no")
            has_drawing = frappe.db.has_column("Item", "custom_drawing_no")

            if has_pl or has_drawing:
                select_fields = ["name"]
                if has_pl:
                    select_fields.append("custom_pl_no")
                if has_drawing:
                    select_fields.append("custom_drawing_no")

                fields_str = ", ".join(select_fields)

                item_data = frappe.db.sql(f"""
                    SELECT {fields_str}
                    FROM `tabItem`
                    WHERE name = %s
                    LIMIT 1
                """, item_row.item, as_dict=True)

                if item_data:
                    if has_pl and "custom_pl_no" in item_data[0]:
                        item_row.pl_no = item_data[0].custom_pl_no
                    if has_drawing and "custom_drawing_no" in item_data[0]:
                        item_row.drawing_no = item_data[0].custom_drawing_no

        product = frappe.db.get_value(
            "PEPL Product Master",
            {"linked_item": item_row.item},
            ["name", "current_drawing_revision", "drawing_number", "pl_number"],
            as_dict=True
        )

        if product:
            item_row.current_drawing_revision = product.current_drawing_revision

            if not item_row.pl_no and product.pl_number:
                item_row.pl_no = product.pl_number

            if not item_row.drawing_no and product.drawing_number:
                item_row.drawing_no = product.drawing_number

            primary_spec = frappe.db.sql("""
                SELECT spec_title FROM `tabPEPL Product Specification`
                WHERE parent = %s AND status = 'Active'
                ORDER BY creation ASC LIMIT 1
            """, product.name, as_dict=True)

            if primary_spec:
                item_row.current_specification = primary_spec[0].spec_title

        vas = frappe.db.get_value(
            "Vendor Approval Status",
            {"item": item_row.item, "sector": self.sector},
            ["railways_stage", "defence_stage"],
            as_dict=True
        )
        if vas:
            if self.sector == "Railways":
                item_row.vendor_approval_stage = vas.railways_stage or "Unapproved"
            elif self.sector == "Defence":
                item_row.vendor_approval_stage = vas.defence_stage or "Source Development"
        else:
            item_row.vendor_approval_stage = "No Record"

    def _calculate_summary(self):
        """Server-side recalculation of row totals — independent of JS state."""
        if not self.items:
            return

        for item in self.items:
            qty = flt(item.quantity) or 0
            est_unit = flt(item.estimated_unit_price) or 0
            our_unit = flt(item.our_bid_unit_price) or 0

            item.estimated_total_value = qty * est_unit
            item.our_bid_total_value = qty * our_unit

        self.total_estimated_value = sum(flt(i.estimated_total_value) for i in self.items)
        self.total_bid_value = sum(flt(i.our_bid_total_value) for i in self.items)

        self.items_won = sum(1 for i in self.items if i.outcome == "Won")
        self.items_lost = sum(1 for i in self.items if i.outcome == "Lost")

        total_decided = self.items_won + self.items_lost
        if total_decided > 0:
            self.win_rate = (self.items_won / total_decided) * 100
        else:
            self.win_rate = 0

    def _update_overall_status(self):
        """Derive tender-level status from item-level outcomes.
        Skip auto-update if status is already 'Order Received' — SO is locked."""

        if self.status == "Order Received":
            return

        if not self.items:
            return

        outcomes = [i.outcome for i in self.items if i.outcome]
        if not outcomes:
            return

        if all(o == "Won" for o in outcomes) and len(outcomes) == len(self.items):
            self.status = "Won"
        elif all(o == "Lost" for o in outcomes) and len(outcomes) == len(self.items):
            self.status = "Lost"
        elif "Won" in outcomes and "Lost" in outcomes:
            self.status = "Partially Won"

    def _process_po_schedule(self):
        """Process PO Schedule rows:
        1. Auto-fetch PL Number and Drawing Number from Item
        2. Recalculate po_total per row (qty x rate)
        3. Flag is_in_won_list (1 if item is in Won tender items, 0 otherwise)
        4. Sum total to po_amount_received on parent
        """
        if not self.po_schedule:
            self.po_amount_received = 0
            return

        # Build set of Won item codes from tender items
        won_item_codes = set()
        if self.items:
            for tender_item in self.items:
                if tender_item.outcome == "Won":
                    won_item_codes.add(tender_item.item)

        # Cache has_column results — avoid repeated DB checks per row
        has_pl = frappe.db.has_column("Item", "custom_pl_no")
        has_drawing = frappe.db.has_column("Item", "custom_drawing_no")

        total = 0
        for schedule_row in self.po_schedule:
            # Auto-fetch PL/Drawing from Item
            if schedule_row.item and (has_pl or has_drawing):
                select_fields = ["name"]
                if has_pl:
                    select_fields.append("custom_pl_no")
                if has_drawing:
                    select_fields.append("custom_drawing_no")

                fields_str = ", ".join(select_fields)
                item_data = frappe.db.sql(f"""
                    SELECT {fields_str}
                    FROM `tabItem`
                    WHERE name = %s
                    LIMIT 1
                """, schedule_row.item, as_dict=True)

                if item_data:
                    if has_pl and "custom_pl_no" in item_data[0]:
                        schedule_row.pl_no = item_data[0].custom_pl_no
                    if has_drawing and "custom_drawing_no" in item_data[0]:
                        schedule_row.drawing_no = item_data[0].custom_drawing_no

            # Flag if item is in Won list
            if schedule_row.item:
                schedule_row.is_in_won_list = 1 if schedule_row.item in won_item_codes else 0

            # Recalc po_total
            qty = flt(schedule_row.po_quantity) or 0
            rate = flt(schedule_row.po_rate) or 0
            schedule_row.po_total = qty * rate
            total += schedule_row.po_total

        self.po_amount_received = total


@frappe.whitelist()
def auto_populate_bid_documents(tender_name):
    """Auto-populate bid documents based on items' Vendor Approval Status."""

    tender = frappe.get_doc("PEPL Tender", tender_name)

    if not tender.items:
        frappe.throw(_("Add tender items first before generating document checklist"))

    sector = tender.sector
    if not sector:
        frappe.throw(_("Sector must be set on tender"))

    stages_seen = set()
    for item_row in tender.items:
        if item_row.vendor_approval_stage:
            stages_seen.add(item_row.vendor_approval_stage)

    from pepl_sales.pepl_sales.doctype.vendor_approval_status.vendor_approval_status import get_required_documents

    all_required_docs = set()
    for stage in stages_seen:
        if stage and stage != "No Record":
            required = get_required_documents(sector, stage)
            if isinstance(required, list):
                all_required_docs.update(required)

    # Always add baseline if no stages had data
    if not all_required_docs:
        baseline = get_required_documents(sector, "Unapproved")
        if isinstance(baseline, list):
            all_required_docs.update(baseline)

    existing_doc_types = {d.document_type for d in tender.bid_documents}
    added = 0
    for doc_type in all_required_docs:
        if doc_type not in existing_doc_types:
            tender.append("bid_documents", {
                "document_source": "Auto-Required",
                "document_type": doc_type,
                "is_mandatory": 1,
                "is_attached": 0
            })
            added += 1

    tender.save()
    return {"added": added, "total_required": len(all_required_docs)}


@frappe.whitelist()
def get_tender_summary(filters=None):
    """Returns aggregated tender pipeline summary for dashboards."""

    summary = frappe.db.sql("""
        SELECT
            sector,
            status,
            COUNT(*) as count,
            SUM(total_estimated_value) as total_estimated,
            SUM(total_bid_value) as total_bid,
            SUM(items_won) as items_won_count
        FROM `tabPEPL Tender`
        GROUP BY sector, status
        ORDER BY sector, status
    """, as_dict=True)

    return summary


def _custom_field_exists_on_so(field_name):
    """Check if a custom field column exists on tabSales Order."""
    try:
        result = frappe.db.sql("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'tabSales Order'
              AND COLUMN_NAME = %s
            LIMIT 1
        """, field_name)
        return len(result) > 0
    except Exception:
        return False


@frappe.whitelist()
def create_sales_order_from_tender(tender_name):
    """Create Sales Order from Tender PO Schedule.
    Each PO Schedule row becomes a separate SO line item with its own delivery date.

    Validation gates:
    - Tender must be Won or Partially Won
    - Customer PO must be received
    - PO Number and PO Date required
    - PO Schedule must have at least one row
    - No existing linked Sales Order (prevents duplicates)
    """

    tender = frappe.get_doc("PEPL Tender", tender_name)

    if tender.status not in ["Won", "Partially Won"]:
        frappe.throw(
            _("Tender must be in 'Won' or 'Partially Won' status. Current status: {0}").format(
                tender.status
            )
        )

    if not tender.customer_po_received:
        frappe.throw(
            _("Customer PO/LOA must be received before creating Sales Order. "
              "Tick 'Customer PO/LOA Received' first.")
        )

    if not tender.po_number:
        frappe.throw(_("Customer PO Number is required"))

    if not tender.po_date:
        frappe.throw(_("Customer PO Date is required"))

    if tender.linked_sales_order:
        frappe.throw(
            _("Sales Order {0} is already linked to this tender. "
              "Delete the existing Sales Order first if you want to recreate.").format(
                tender.linked_sales_order
            )
        )

    if not tender.po_schedule:
        frappe.throw(_("PO Schedule is empty. Add at least one delivery line."))

    # Validate each schedule row
    for idx, schedule_row in enumerate(tender.po_schedule, start=1):
        if not schedule_row.item:
            frappe.throw(_("Row {0}: Item is required").format(idx))
        if not schedule_row.po_quantity or schedule_row.po_quantity <= 0:
            frappe.throw(_("Row {0}: PO Quantity must be greater than 0").format(idx))
        if not schedule_row.po_rate or schedule_row.po_rate <= 0:
            frappe.throw(_("Row {0}: PO Rate must be greater than 0").format(idx))
        if not schedule_row.delivery_date:
            frappe.throw(_("Row {0}: Delivery Date is required").format(idx))

    # Set SO header delivery_date as earliest from schedule
    earliest_delivery = min(
        (s.delivery_date for s in tender.po_schedule if s.delivery_date),
        default=None
    )

    so = frappe.new_doc("Sales Order")
    so.customer = tender.customer
    so.po_no = tender.po_number
    so.po_date = tender.po_date
    so.delivery_date = earliest_delivery or add_days(today(), 30)
    so.transaction_date = today()

    if tender.po_payment_terms:
        so.payment_terms_template = tender.po_payment_terms

    if _custom_field_exists_on_so("custom_tender_reference"):
        so.custom_tender_reference = tender.name

    if _custom_field_exists_on_so("custom_nit_number"):
        so.custom_nit_number = tender.nit_number

    if _custom_field_exists_on_so("custom_sector"):
        so.custom_sector = tender.sector

    # One SO line per PO Schedule row (preserves multiplicity + per-line delivery dates)
    for schedule_row in tender.po_schedule:
        so.append("items", {
            "item_code": schedule_row.item,
            "qty": schedule_row.po_quantity,
            "rate": schedule_row.po_rate,
            "delivery_date": schedule_row.delivery_date
        })

    so.insert(ignore_permissions=True)

    tender.linked_sales_order = so.name
    tender.status = "Order Received"
    tender.save(ignore_permissions=True)

    return {
        "sales_order": so.name,
        "url": f"/app/sales-order/{so.name}",
        "lines_added": len(tender.po_schedule),
        "total_value": flt(tender.po_amount_received)
    }
