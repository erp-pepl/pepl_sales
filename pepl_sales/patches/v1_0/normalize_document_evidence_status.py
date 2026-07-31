import frappe


COMPLETED_STATUSES = {
    "Received",
    "Filed",
}

NON_RECEIVED_STATUSES = {
    "Pending",
    "Obsolete",
}


def execute():
    """
    Normalize historical PEPL Document Tracker evidence state.

    Rules:
    - Received and Filed require attachment, received date, and user.
    - Incomplete completed rows are reset to Pending.
    - Pending and Obsolete rows cannot retain receipt metadata.
    - Safe to execute repeatedly.
    """

    tracker_names = frappe.get_all(
        "PEPL Document Tracker",
        pluck="name",
        limit_page_length=0,
    )

    trackers_updated = 0
    completed_rows_reset = 0
    pending_rows_cleaned = 0

    for tracker_name in tracker_names:
        tracker = frappe.get_doc(
            "PEPL Document Tracker",
            tracker_name,
        )

        tracker_changed = False

        for row in tracker.document_entries or []:
            status = (row.document_status or "").strip()

            if status in COMPLETED_STATUSES:
                has_complete_evidence = (
                    bool(row.receipt_attachment)
                    and bool(row.received_date)
                    and bool(row.received_by)
                )

                if not has_complete_evidence:
                    row.document_status = "Pending"
                    row.receipt_attachment = None
                    row.received_date = None
                    row.received_by = None

                    tracker_changed = True
                    completed_rows_reset += 1

            elif status in NON_RECEIVED_STATUSES:
                has_receipt_metadata = (
                    bool(row.receipt_attachment)
                    or bool(row.received_date)
                    or bool(row.received_by)
                )

                if has_receipt_metadata:
                    row.receipt_attachment = None
                    row.received_date = None
                    row.received_by = None

                    tracker_changed = True
                    pending_rows_cleaned += 1

        if tracker_changed:
            tracker.save(ignore_permissions=True)
            trackers_updated += 1

    frappe.logger("pepl_sales").info(
        {
            "event": "normalize_document_evidence_status",
            "trackers_updated": trackers_updated,
            "completed_rows_reset": completed_rows_reset,
            "pending_rows_cleaned": pending_rows_cleaned,
        }
    )
