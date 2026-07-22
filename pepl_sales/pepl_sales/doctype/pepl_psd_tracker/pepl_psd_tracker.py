import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, flt, getdate


VALID_PSD_SECTORS = {
    "Railways",
    "Defence",
    "Private",
    "Others",
}


def normalize_psd_sector(value):
    """
    Normalize supported PEPL sector values.

    Returns one of:
        Railways
        Defence
        Private
        Others

    Returns None when a populated value cannot be mapped.
    """
    normalized = (value or "").strip().lower()

    if not normalized:
        return None

    mapping = {
        "railway": "Railways",
        "railways": "Railways",
        "defence": "Defence",
        "defense": "Defence",
        "private": "Private",
        "private sector": "Private",
        "others": "Others",
        "other": "Others",
        "commercial": "Others",
    }

    return mapping.get(normalized)


def get_psd_sector_from_sales_order(sales_order):
    """
    Resolve the PSD Tracker sector from a Sales Order.

    Priority:
        1. Sales Order.custom_sector
        2. Customer.customer_group as a legacy fallback
        3. Others when neither source provides a usable sector

    A populated but unknown Sales Order sector is treated as a data error and
    must not silently fall back to Others.
    """
    source_sector = sales_order.get("custom_sector")

    if source_sector:
        resolved_sector = normalize_psd_sector(source_sector)

        if not resolved_sector:
            frappe.throw(
                _(
                    "Unable to map Sales Order sector '{0}' "
                    "to a PEPL PSD Tracker sector."
                ).format(source_sector)
            )

        return resolved_sector

    customer_group = ""

    if sales_order.customer:
        customer_group = (
            frappe.db.get_value(
                "Customer",
                sales_order.customer,
                "customer_group",
            )
            or ""
        )

    fallback_sector = normalize_psd_sector(customer_group)

    return fallback_sector or "Others"


class PEPLPSDTracker(Document):
    def validate(self):
        self._validate_linked_sales_order()
        self._synchronise_sector_from_sales_order()
        self._recalculate_entries()
        self._recalculate_summary()
        self._set_tracker_id()

    def _validate_linked_sales_order(self):
        if not self.linked_sales_order:
            return

        if not frappe.db.exists(
            "Sales Order",
            self.linked_sales_order,
        ):
            frappe.throw(
                _(
                    "Linked Sales Order {0} does not exist."
                ).format(self.linked_sales_order)
            )

    def _synchronise_sector_from_sales_order(self):
        """
        Keep the Tracker sector aligned with its linked Sales Order.

        The Sales Order sector is authoritative. This also repairs a Tracker
        when it is saved after previously being classified as Others.
        """
        if not self.linked_sales_order:
            return

        sales_order = frappe.get_doc(
            "Sales Order",
            self.linked_sales_order,
        )

        resolved_sector = get_psd_sector_from_sales_order(
            sales_order
        )

        if resolved_sector not in VALID_PSD_SECTORS:
            frappe.throw(
                _(
                    "Resolved PSD sector '{0}' is invalid."
                ).format(resolved_sector)
            )

        self.sector = resolved_sector

    def _recalculate_entries(self):
        for entry in self.psd_entries or []:
            if not entry.manual_override:
                if (
                    entry.order_value_basis
                    and entry.psd_percent is not None
                ):
                    entry.psd_amount = (
                        flt(entry.order_value_basis)
                        * flt(entry.psd_percent)
                        / 100
                    )

            if (
                flt(entry.psd_percent) == 0
                and entry.psd_status == "Pending"
            ):
                entry.psd_status = "PSD Not Required"

            if (
                entry.last_supply_date
                and not entry.expected_refund_date
            ):
                entry.expected_refund_date = add_months(
                    getdate(entry.last_supply_date),
                    14,
                )

    def _recalculate_summary(self):
        entries = self.psd_entries or []

        self.active_entries_count = sum(
            1
            for entry in entries
            if entry.psd_status
            not in [
                "Closed",
                "PSD Not Required",
            ]
        )

        self.total_psd_amount = sum(
            flt(entry.psd_amount)
            for entry in entries
        )

    def _set_tracker_id(self):
        if not self.tracker_id:
            self.tracker_id = self.name

    def _fetch_sector_from_so(self):
        """
        Backward-compatible wrapper retained for any existing callers.
        """
        self._synchronise_sector_from_sales_order()


@frappe.whitelist()
def create_psd_tracker_for_so(sales_order_name):
    """
    Create one PSD Tracker per submitted Sales Order.

    The function is idempotent. Repeated calls return the existing Tracker
    rather than creating a duplicate.
    """
    if not sales_order_name:
        frappe.throw(
            _("Sales Order name is required.")
        )

    existing = frappe.db.exists(
        "PEPL PSD Tracker",
        {
            "linked_sales_order": sales_order_name,
        },
    )

    if existing:
        return {
            "created": False,
            "tracker_name": existing,
        }

    sales_order = frappe.get_doc(
        "Sales Order",
        sales_order_name,
    )

    if sales_order.docstatus != 1:
        frappe.throw(
            _(
                "PSD Tracker can only be created from a "
                "submitted Sales Order."
            )
        )

    sector = get_psd_sector_from_sales_order(
        sales_order
    )

    configured_default_percent = flt(
        frappe.db.get_single_value(
            "PEPL System Parameters",
            "psd_default_percent",
        )
    )

    # Existing approved business rule:
    # the configured default PSD percentage is applied only to Defence.
    default_percent = (
        configured_default_percent
        if sector == "Defence"
        else 0
    )

    initial_amount = (
        flt(sales_order.grand_total)
        * default_percent
        / 100
    )

    initial_status = (
        "Pending"
        if default_percent > 0
        else "PSD Not Required"
    )

    tracker = frappe.new_doc(
        "PEPL PSD Tracker"
    )

    tracker.linked_sales_order = sales_order.name
    tracker.customer = sales_order.customer
    tracker.sector = sector

    tracker.append(
        "psd_entries",
        {
            "entry_label": "Initial PSD",
            "psd_status": initial_status,
            "psd_percent": default_percent,
            "psd_amount": initial_amount,
            "order_value_basis": sales_order.grand_total,
        },
    )

    tracker.insert(
        ignore_permissions=True
    )

    return {
        "created": True,
        "tracker_name": tracker.name,
        "sector": sector,
        "percentage": default_percent,
        "initial_amount": initial_amount,
    }
