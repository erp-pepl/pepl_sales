from __future__ import annotations

import frappe
from frappe import _


COMPLETED_DOCUMENT_STATUSES = {
    "Received",
    "Filed",
}

NON_RECEIVED_DOCUMENT_STATUSES = {
    "Pending",
    "Obsolete",
}


def validate_document_tracker(doc, method=None):
    """Validate PEPL Document Tracker child-row consistency.

    Rules:
    - Document Type is mandatory.
    - Duplicate Document Types are prohibited.
    - Received and Filed rows require attachment, date, and user.
    - Pending and Obsolete rows must not retain receipt evidence.
    """

    seen_document_types = set()

    for row in doc.document_entries or []:
        document_type = (row.document_type or "").strip()
        document_status = (row.document_status or "").strip()

        if not document_type:
            frappe.throw(
                _("Document Type is required in row {0}.").format(
                    row.idx
                )
            )

        if document_type in seen_document_types:
            frappe.throw(
                _(
                    "Document Type {0} is duplicated in row {1}."
                ).format(
                    frappe.bold(document_type),
                    row.idx,
                )
            )

        seen_document_types.add(document_type)

        if document_status in COMPLETED_DOCUMENT_STATUSES:
            missing_fields = []

            if not row.receipt_attachment:
                missing_fields.append(_("Receipt Attachment"))

            if not row.received_date:
                missing_fields.append(_("Received Date"))

            if not row.received_by:
                missing_fields.append(_("Received By"))

            if missing_fields:
                frappe.throw(
                    _(
                        "Row {0}: {1} cannot be marked as {2}. "
                        "Missing evidence: {3}."
                    ).format(
                        row.idx,
                        frappe.bold(document_type),
                        frappe.bold(document_status),
                        ", ".join(missing_fields),
                    )
                )

        if document_status in NON_RECEIVED_DOCUMENT_STATUSES:
            inconsistent_fields = []

            if row.received_date:
                inconsistent_fields.append(_("Received Date"))

            if row.received_by:
                inconsistent_fields.append(_("Received By"))

            if row.receipt_attachment:
                inconsistent_fields.append(_("Receipt Attachment"))

            if inconsistent_fields:
                frappe.throw(
                    _(
                        "Row {0}: {1} is marked as {2}, but contains "
                        "receipt information: {3}. Clear these values "
                        "or change the status."
                    ).format(
                        row.idx,
                        frappe.bold(document_type),
                        frappe.bold(document_status),
                        ", ".join(inconsistent_fields),
                    )
                )
