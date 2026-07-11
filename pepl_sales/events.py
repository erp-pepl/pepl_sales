import frappe


def on_sales_order_submit(doc, method=None):
    """
    Create Cycle 1 trackers when a Sales Order is submitted.

    This wrapper receives the Sales Order document from Frappe's
    doc_events system and passes its name to the existing services.
    """

    from pepl_sales.pepl_sales.doctype.pepl_document_tracker.pepl_document_tracker import (
        create_doc_tracker_for_so,
    )
    from pepl_sales.pepl_sales.doctype.pepl_psd_tracker.pepl_psd_tracker import (
        create_psd_tracker_for_so,
    )

    create_psd_tracker_for_so(doc.name)

    source_tender = None

    if frappe.db.has_column("Sales Order", "custom_tender_reference"):
        source_tender = doc.get("custom_tender_reference")

    create_doc_tracker_for_so(
        sales_order_name=doc.name,
        source_tender=source_tender,
    )


def on_sales_invoice_submit(doc, method=None):
    """
    Activate Payment Tracker when a Sales Invoice is submitted.
    """

    from pepl_sales.pepl_sales.doctype.pepl_payment_tracker.pepl_payment_tracker import (
        create_payment_tracker_for_invoice,
    )

    create_payment_tracker_for_invoice(doc.name)
