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


def on_payment_entry_submit(doc, method=None):
    """
    Synchronize submitted ERPNext customer Payment Entries into PEPL.

    Accounting submission is not blocked if the PEPL operational sync fails.
    The failure is logged and shown to the user for correction.
    """

    try:
        from pepl_sales.overrides.payment_entry import (
            sync_payment_entry,
        )

        return sync_payment_entry(doc)

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "PEPL Payment Entry Submit Sync Failed",
        )

        frappe.msgprint(
            (
                "The ERPNext Payment Entry was processed, but PEPL "
                "Payment Tracker synchronization encountered an error. "
                "Please review the Error Log before UAT sign-off."
            ),
            indicator="orange",
        )


def on_payment_entry_cancel(doc, method=None):
    """
    Reverse PEPL receipt synchronization when Payment Entry is cancelled.
    """

    try:
        from pepl_sales.overrides.payment_entry import (
            unsync_payment_entry,
        )

        return unsync_payment_entry(doc)

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "PEPL Payment Entry Cancel Sync Failed",
        )

        frappe.msgprint(
            (
                "The ERPNext Payment Entry was cancelled, but PEPL "
                "Payment Tracker reversal encountered an error. "
                "Please review the Error Log."
            ),
            indicator="orange",
        )
