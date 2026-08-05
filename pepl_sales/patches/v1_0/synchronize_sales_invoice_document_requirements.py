import frappe


def execute():
    """Synchronize invoice-stage requirements for submitted invoices.

    The synchronization routine is idempotent. A failure concerning
    one historical invoice is logged without stopping all remaining
    invoices from being processed.
    """
    from pepl_sales.pepl_sales.doctype.pepl_document_tracker.document_requirement_sync import (
        synchronize_sales_invoice_requirements,
    )

    invoice_names = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
        },
        pluck="name",
        order_by="creation asc",
        limit_page_length=100000,
    )

    for invoice_name in invoice_names:
        try:
            invoice = frappe.get_doc(
                "Sales Invoice",
                invoice_name,
            )

            synchronize_sales_invoice_requirements(
                invoice
            )

        except Exception:
            frappe.log_error(
                title=(
                    "Sales Invoice document requirement "
                    "synchronization failed: "
                    + invoice_name
                ),
                message=frappe.get_traceback(),
            )
