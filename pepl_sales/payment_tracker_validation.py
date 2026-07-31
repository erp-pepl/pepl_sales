from __future__ import annotations

import frappe
from frappe import _


def validate_payment_tracker(doc, method=None):
    """Protect PEPL Payment Tracker source integrity.

    A Payment Tracker must reference an existing submitted Sales Invoice.
    This prevents manual, imported, or API-created trackers from being
    linked to draft or cancelled invoices.
    """

    invoice_name = (doc.linked_sales_invoice or "").strip()

    if not invoice_name:
        frappe.throw(
            _("Linked Sales Invoice is mandatory.")
        )

    invoice = frappe.db.get_value(
        "Sales Invoice",
        invoice_name,
        [
            "name",
            "docstatus",
            "customer",
            "posting_date",
            "grand_total",
            "outstanding_amount",
        ],
        as_dict=True,
    )

    if not invoice:
        frappe.throw(
            _(
                "Linked Sales Invoice {0} does not exist."
            ).format(
                frappe.bold(invoice_name)
            )
        )

    if invoice.docstatus != 1:
        status_label = {
            0: _("Draft"),
            2: _("Cancelled"),
        }.get(
            invoice.docstatus,
            str(invoice.docstatus),
        )

        frappe.throw(
            _(
                "Payment Tracker cannot reference Sales Invoice "
                "{0} because it is {1}. Submit the Sales Invoice "
                "before creating its Payment Tracker."
            ).format(
                frappe.bold(invoice_name),
                frappe.bold(status_label),
            )
        )

    if doc.customer and doc.customer != invoice.customer:
        frappe.throw(
            _(
                "Payment Tracker Customer {0} does not match "
                "Sales Invoice Customer {1}."
            ).format(
                frappe.bold(doc.customer),
                frappe.bold(invoice.customer),
            )
        )
