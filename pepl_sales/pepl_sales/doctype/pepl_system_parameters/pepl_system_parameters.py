# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd.
# and contributors

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class PEPLSystemParameters(Document):
    def validate(self):
        self._validate_cycle_thresholds()
        self._validate_percentage_parameters()
        self._validate_ageing_thresholds()
        self._validate_alert_windows()
        self._validate_notification_configuration()

    def _validate_cycle_thresholds(self):
        low = flt(self.cycle_deviation_threshold_low)
        high = flt(self.cycle_deviation_threshold_high)

        if low <= 0:
            frappe.throw(
                _("Cycle Deviation Threshold Low must be greater than zero.")
            )

        if high <= low:
            frappe.throw(
                _(
                    "Cycle Deviation Threshold High must be greater "
                    "than Cycle Deviation Threshold Low."
                )
            )

    def _validate_percentage_parameters(self):
        percentage_fields = {
            "psd_default_percent": _("PSD Default Percentage"),
            "margin_floor_percent": _("Minimum Margin Floor"),
        }

        for fieldname, label in percentage_fields.items():
            value = flt(self.get(fieldname))

            if value < 0 or value > 100:
                frappe.throw(
                    _("{0} must be between 0 and 100.").format(label)
                )

    def _validate_ageing_thresholds(self):
        amber_days = cint(self.payment_ageing_amber_days)
        red_days = cint(self.payment_ageing_red_days)

        if amber_days <= 0:
            frappe.throw(
                _("Payment Ageing Amber Days must be greater than zero.")
            )

        if red_days <= amber_days:
            frappe.throw(
                _(
                    "Payment Ageing Red Days must be greater than "
                    "Payment Ageing Amber Days."
                )
            )

    def _validate_alert_windows(self):
        alert_fields = {
            "psd_expiry_alert_days": _("PSD Expiry Alert Days"),
            "vendor_approval_expiry_alert_days": _(
                "Vendor Approval Expiry Alert Days"
            ),
            "tender_deadline_alert_days": _("Tender Deadline Alert Days"),
            "document_pending_alert_days": _("Document Pending Alert Days"),
            "material_receipt_alert_days": _("Material Receipt Alert Days"),
        }

        for fieldname, label in alert_fields.items():
            if cint(self.get(fieldname)) < 0:
                frappe.throw(
                    _("{0} cannot be negative.").format(label)
                )

    def _validate_notification_configuration(self):
        if not cint(self.enable_operational_todos):
            return

        functional_owners = [
            self.sales_notification_owner,
            self.accounts_notification_owner,
            self.engineering_notification_owner,
        ]

        if not any(functional_owners) and not self.notification_fallback_owner:
            frappe.throw(
                _(
                    "Assign at least one functional notification owner "
                    "or a Notification Fallback Owner before enabling "
                    "Daily Operational ToDos."
                )
            )


def get_param(field_name, default=None):
    """Safely read a PEPL System Parameter."""
    try:
        value = frappe.db.get_single_value(
            "PEPL System Parameters",
            field_name,
        )

        return default if value in (None, "") else value

    except Exception:
        return default