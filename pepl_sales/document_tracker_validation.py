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


def _get_managed_requirement_key(row):
    """Return the unique identity of an auto-managed row.

    Sales Invoice requirements are scoped to the individual invoice.
    Sales Order and other managed requirements retain one active row
    per requirement under the tracker.
    """
    requirement_code = (
        row.get("requirement_code")
        or row.get("requirement")
        or ""
    ).strip()

    source_transaction = (
        row.get(
            "requirement_source_transaction"
        )
        or ""
    ).strip()

    source_reference = (
        row.get("source_reference")
        or ""
    ).strip()

    if (
        source_transaction
        == "Sales Invoice"
    ):
        return (
            requirement_code,
            source_transaction,
            source_reference,
        )

    return (
        requirement_code,
        source_transaction,
        "",
    )


def validate_document_tracker(
    doc,
    method=None,
):
    """Validate PEPL Document Tracker child-row consistency.

    Rules:
    - Document Type is mandatory.
    - Manual rows may not repeat a Document Type.
    - Managed rows are unique by requirement and source context.
    - Multiple Sales Invoices may use the same Document Type.
    - Received and Filed rows require evidence.
    - Pending and Obsolete rows may not retain receipt evidence.
    """
    seen_manual_document_types = set()
    seen_managed_keys = set()

    for row in doc.document_entries or []:
        document_type = (
            row.document_type
            or ""
        ).strip()

        document_status = (
            row.document_status
            or ""
        ).strip()

        if not document_type:
            frappe.throw(
                _(
                    "Document Type is required "
                    "in row {0}."
                ).format(
                    row.idx
                )
            )

        if row.get(
            "is_managed_requirement"
        ):
            managed_key = (
                _get_managed_requirement_key(
                    row
                )
            )

            if not managed_key[0]:
                frappe.throw(
                    _(
                        "Managed Document Entry row {0} "
                        "has no Requirement Code."
                    ).format(
                        row.idx
                    )
                )

            if (
                managed_key[1]
                == "Sales Invoice"
                and not managed_key[2]
            ):
                frappe.throw(
                    _(
                        "Managed Sales Invoice requirement "
                        "row {0} has no source invoice."
                    ).format(
                        row.idx
                    )
                )

            if (
                managed_key
                in seen_managed_keys
            ):
                source_label = (
                    managed_key[2]
                    or managed_key[1]
                    or _("configured source")
                )

                frappe.throw(
                    _(
                        "Requirement {0} is duplicated "
                        "for source {1} in row {2}."
                    ).format(
                        frappe.bold(
                            managed_key[0]
                        ),
                        frappe.bold(
                            source_label
                        ),
                        row.idx,
                    )
                )

            seen_managed_keys.add(
                managed_key
            )

        else:
            if (
                document_type
                in seen_manual_document_types
            ):
                frappe.throw(
                    _(
                        "Manual Document Type {0} "
                        "is duplicated in row {1}."
                    ).format(
                        frappe.bold(
                            document_type
                        ),
                        row.idx,
                    )
                )

            seen_manual_document_types.add(
                document_type
            )

        if (
            document_status
            in COMPLETED_DOCUMENT_STATUSES
        ):
            missing_fields = []

            if not row.receipt_attachment:
                missing_fields.append(
                    _("Receipt Attachment")
                )

            if not row.received_date:
                missing_fields.append(
                    _("Received Date")
                )

            if not row.received_by:
                missing_fields.append(
                    _("Received By")
                )

            if missing_fields:
                frappe.throw(
                    _(
                        "Row {0}: {1} cannot be "
                        "marked as {2}. Missing "
                        "evidence: {3}."
                    ).format(
                        row.idx,
                        frappe.bold(
                            document_type
                        ),
                        frappe.bold(
                            document_status
                        ),
                        ", ".join(
                            missing_fields
                        ),
                    )
                )

        if (
            document_status
            in NON_RECEIVED_DOCUMENT_STATUSES
        ):
            inconsistent_fields = []

            if row.received_date:
                inconsistent_fields.append(
                    _("Received Date")
                )

            if row.received_by:
                inconsistent_fields.append(
                    _("Received By")
                )

            if row.receipt_attachment:
                inconsistent_fields.append(
                    _("Receipt Attachment")
                )

            if inconsistent_fields:
                frappe.throw(
                    _(
                        "Row {0}: {1} is marked "
                        "as {2}, but contains "
                        "receipt information: {3}. "
                        "Clear these values or "
                        "change the status."
                    ).format(
                        row.idx,
                        frappe.bold(
                            document_type
                        ),
                        frappe.bold(
                            document_status
                        ),
                        ", ".join(
                            inconsistent_fields
                        ),
                    )
                )
