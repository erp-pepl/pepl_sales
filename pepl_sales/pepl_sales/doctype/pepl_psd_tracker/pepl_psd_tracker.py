import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, add_months


class PEPLPSDTracker(Document):
    def validate(self):
        # Auto-fetch sector from SO's customer if not set
        if self.linked_sales_order and not self.sector:
            self._fetch_sector_from_so()

        # Step 1: Server-side recalculation of each PSD Entry
        # (Child validate doesn't fire on parent save — must do here)
        if self.psd_entries:
            for entry in self.psd_entries:
                # Auto-calculate PSD amount UNLESS manual override is on
                if not entry.manual_override:
                    if entry.order_value_basis and entry.psd_percent is not None:
                        entry.psd_amount = flt(entry.order_value_basis) * flt(entry.psd_percent) / 100

                # Auto-set status to "PSD Not Required" if 0%
                if flt(entry.psd_percent) == 0 and entry.psd_status == "Pending":
                    entry.psd_status = "PSD Not Required"

                # Auto-calculate expected refund date if last_supply_date set
                if entry.last_supply_date and not entry.expected_refund_date:
                    entry.expected_refund_date = add_months(getdate(entry.last_supply_date), 14)

        # Step 2: Recalculate Tracker summary fields from entries
        if self.psd_entries:
            self.active_entries_count = sum(
                1 for e in self.psd_entries
                if e.psd_status not in ["Closed", "PSD Not Required"]
            )
            self.total_psd_amount = sum(flt(e.psd_amount) for e in self.psd_entries)
        else:
            self.active_entries_count = 0
            self.total_psd_amount = 0

        # Step 3: Set tracker_id from name
        if not self.tracker_id:
            self.tracker_id = self.name

    def _fetch_sector_from_so(self):
        customer = frappe.db.get_value("Sales Order", self.linked_sales_order, "customer")
        if not customer:
            return
        cg = frappe.db.get_value("Customer", customer, "customer_group")
        if not cg:
            return
        if "Railway" in cg:
            self.sector = "Railways"
        elif "Defence" in cg:
            self.sector = "Defence"
        elif "Private" in cg:
            self.sector = "Private"
        else:
            self.sector = "Others"


@frappe.whitelist()
def create_psd_tracker_for_so(sales_order_name):
    """Create one PSD Tracker per Sales Order with one default PSD Entry.
    Idempotent — returns existing tracker if already created.
    """
    existing = frappe.db.exists("PEPL PSD Tracker", {"linked_sales_order": sales_order_name})
    if existing:
        return {"created": False, "tracker_name": existing}

    so = frappe.get_doc("Sales Order", sales_order_name)

    sector = "Others"
    if so.customer:
        cg = frappe.db.get_value("Customer", so.customer, "customer_group")
        if cg:
            if "Railway" in cg:
                sector = "Railways"
            elif "Defence" in cg:
                sector = "Defence"
            elif "Private" in cg:
                sector = "Private"

    configured_default_percent = flt(
        frappe.db.get_single_value(
            "PEPL System Parameters",
            "psd_default_percent",
        )
    )

    default_percent = (
        configured_default_percent
        if sector == "Defence"
        else 0
    )

    initial_amount = (
        flt(so.grand_total)
        * default_percent
        / 100
    )
    initial_status = "Pending" if default_percent > 0 else "PSD Not Required"

    tracker = frappe.new_doc("PEPL PSD Tracker")
    tracker.linked_sales_order = so.name
    tracker.customer = so.customer
    tracker.sector = sector

    tracker.append("psd_entries", {
        "entry_label": "Initial PSD",
        "psd_status": initial_status,
        "psd_percent": default_percent,
        "psd_amount": initial_amount,
        "order_value_basis": so.grand_total
    })

    tracker.insert(ignore_permissions=True)

    return {
        "created": True,
        "tracker_name": tracker.name,
        "sector": sector,
        "percentage": default_percent,
        "initial_amount": initial_amount
    }
