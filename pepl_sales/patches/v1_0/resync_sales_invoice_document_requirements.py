import frappe


def execute():
    """Retry Sales Invoice requirement synchronization.

    This patch runs after the PEPL Document Entry Select options
    have been expanded to include all invoice-stage document types.
    """
    from pepl_sales.pepl_sales.doctype.pepl_document_tracker.document_requirement_sync import (
        synchronize_sales_invoice_requirements,
    )

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
        },
        pluck="name",
        order_by="creation asc",
        limit_page_length=100000,
    )

    failures = []

    for invoice_name in invoices:
        invoice = frappe.get_doc(
            "Sales Invoice",
            invoice_name,
        )

        linked_sales_orders = {
            row.get("sales_order")
            for row in invoice.get("items") or []
            if row.get("sales_order")
        }

        if not linked_sales_orders:
            continue

        try:
            synchronize_sales_invoice_requirements(
                invoice
            )

        except Exception:
            failures.append(
                invoice_name
            )

            frappe.log_error(
                title=(
                    "Sales Invoice document requirement "
                    "resynchronization failed: "
                    + invoice_name
                ),
                message=frappe.get_traceback(),
            )

    if failures:
        frappe.throw(
            "Sales Invoice requirement resynchronization "
            "failed for: "
            + ", ".join(failures)
        )
