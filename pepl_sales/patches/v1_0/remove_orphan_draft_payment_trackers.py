import frappe


def execute():
    """Remove empty Payment Trackers linked to draft invoices.

    A tracker is deleted only when:
    - its linked Sales Invoice is Draft;
    - it has no Payment Receipt rows;
    - total received is zero;
    - amount reconciled is zero.

    Trackers containing financial activity are preserved and logged for
    manual investigation. The patch is idempotent.
    """

    tracker_names = frappe.get_all(
        "PEPL Payment Tracker",
        pluck="name",
        limit_page_length=0,
    )

    deleted = []
    skipped = []

    for tracker_name in tracker_names:
        tracker = frappe.get_doc(
            "PEPL Payment Tracker",
            tracker_name,
        )

        invoice_name = tracker.linked_sales_invoice

        if not invoice_name:
            skipped.append(
                {
                    "tracker": tracker.name,
                    "reason": "blank_sales_invoice",
                }
            )
            continue

        invoice_docstatus = frappe.db.get_value(
            "Sales Invoice",
            invoice_name,
            "docstatus",
        )

        if invoice_docstatus != 0:
            continue

        receipt_count = len(
            tracker.payment_receipts or []
        )

        total_received = float(
            tracker.total_amount_received or 0
        )

        amount_reconciled = float(
            tracker.amount_reconciled or 0
        )

        has_financial_activity = (
            receipt_count > 0
            or abs(total_received) > 0.01
            or abs(amount_reconciled) > 0.01
        )

        if has_financial_activity:
            skipped.append(
                {
                    "tracker": tracker.name,
                    "invoice": invoice_name,
                    "reason": "financial_activity_exists",
                    "receipt_count": receipt_count,
                    "total_received": total_received,
                    "amount_reconciled": amount_reconciled,
                }
            )
            continue

        frappe.delete_doc(
            "PEPL Payment Tracker",
            tracker.name,
            ignore_permissions=True,
            force=True,
        )

        deleted.append(
            {
                "tracker": tracker.name,
                "invoice": invoice_name,
            }
        )

    frappe.logger("pepl_sales").info(
        {
            "event": "remove_orphan_draft_payment_trackers",
            "deleted_count": len(deleted),
            "deleted": deleted,
            "skipped_count": len(skipped),
            "skipped": skipped,
        }
    )
