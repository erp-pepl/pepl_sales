import frappe
from frappe import _
from frappe.model.document import Document

from pepl_sales.pepl_sales.doctype.pepl_document_entry.pepl_document_entry import (
    COMPLETED_DOCUMENT_STATUSES,
    validate_document_entry,
)


class PEPLDocumentTracker(Document):
    def validate(self):
        self.total_documents = len(self.document_entries or [])

        if not self.tracker_id:
            self.tracker_id = self.name

        self._validate_document_entries()
        self._validate_document_attachments()

    def _validate_document_attachments(self):
        valid_document_types = {
            row.document_type
            for row in self.document_entries or []
            if row.document_type
        }

        for index, row in enumerate(
            self.document_attachments or [],
            start=1,
        ):
            if not row.document_type:
                frappe.throw(
                    _(
                        "Additional Attachment row {0}: "
                        "Related Document Type is required."
                    ).format(index)
                )

            if row.document_type not in valid_document_types:
                frappe.throw(
                    _(
                        "Additional Attachment row {0}: "
                        "Document Type '{1}' does not exist in "
                        "the Document Entries table."
                    ).format(
                        index,
                        row.document_type,
                    )
                )

    def _validate_document_entries(self):
        for index, row in enumerate(
            self.document_entries or [],
            start=1,
        ):
            if (
                row.document_type == "Material Receipt"
                and row.document_status in COMPLETED_DOCUMENT_STATUSES
                and not row.receipt_attachment
            ):
                frappe.throw(
                    _(
                        "Document row {0}: attach the customer receipt or "
                        "material acknowledgement before marking Material "
                        "Receipt as {1}."
                    ).format(
                        index,
                        row.document_status,
                    )
                )

            validate_document_entry(
                row,
                row_number=index,
            )


@frappe.whitelist()
def create_doc_tracker_for_so(
    sales_order_name,
    source_tender=None,
):
    """
    Create or enrich the Document Tracker for a Sales Order.

    This method is intentionally idempotent. If another hook or an
    earlier app version already created the tracker, missing required
    checklist rows are appended without disturbing existing records.
    """

    sales_order = frappe.get_doc(
        "Sales Order",
        sales_order_name,
    )

    existing = frappe.db.exists(
        "PEPL Document Tracker",
        {"linked_sales_order": sales_order_name},
    )

    if existing:
        tracker = frappe.get_doc(
            "PEPL Document Tracker",
            existing,
        )
        created = False
    else:
        tracker = frappe.new_doc(
            "PEPL Document Tracker"
        )
        tracker.linked_sales_order = sales_order.name
        tracker.customer = sales_order.customer
        created = True

    if not tracker.customer:
        tracker.customer = sales_order.customer

    existing_types = {
        row.document_type
        for row in tracker.document_entries or []
        if row.document_type
    }

    added_documents = []

    if "Customer PO" not in existing_types:
        po_title = (
            "Customer PO {0}".format(sales_order.po_no)
            if sales_order.po_no
            else "Customer PO"
        )

        tracker.append(
            "document_entries",
            {
                "document_date":
                    sales_order.po_date
                    or sales_order.transaction_date,
                "document_type": "Customer PO",
                "description": po_title,
                "reference_number": sales_order.po_no or "",
                "direction": "Inbound (from Customer)",
                "document_status": "Received",
                "received_date":
                    sales_order.po_date
                    or sales_order.transaction_date,
                "received_by": frappe.session.user,
                "source": "Auto-Generated",
                "source_reference": sales_order.name,
                "is_required": 1,
            },
        )

        existing_types.add("Customer PO")
        added_documents.append("Customer PO")

    sector = _get_sector_for_sales_order(
        sales_order
    )

    required_documents = {
        "Railways": [
            "Material Receipt",
            "R-Note",
            "CO7",
            "JCC",
        ],
        "Defence": [
            "Material Receipt",
            "I-Note",
            "JCC",
        ],
        "Private": [
            "Material Receipt",
            "JCC",
        ],
        "Others": [
            "Material Receipt",
            "JCC",
        ],
    }

    for document_type in required_documents.get(
        sector,
        required_documents["Others"],
    ):
        if document_type in existing_types:
            continue

        tracker.append(
            "document_entries",
            {
                "document_type": document_type,
                "description": _(
                    "{0} — required for payment or "
                    "receipt confirmation"
                ).format(document_type),
                "direction": "Inbound (from Customer)",
                "document_status": "Pending",
                "document_date": None,
                "received_date": None,
                "received_by": None,
                "source": "Auto-Generated",
                "is_required": 1,
            },
        )

        existing_types.add(document_type)
        added_documents.append(document_type)

    if source_tender:
        nda_exists = any(
            row.document_type == "NDA"
            for row in tracker.document_entries or []
        )

        if not nda_exists:
            before_count = len(
                tracker.document_entries or []
            )

            _copy_tender_nda(
                tracker,
                source_tender,
                sales_order.transaction_date,
            )

            if (
                len(tracker.document_entries or [])
                > before_count
            ):
                added_documents.append("NDA")

    if created:
        tracker.insert(ignore_permissions=True)
    elif added_documents:
        tracker.save(ignore_permissions=True)

    return {
        "created": created,
        "updated": bool(added_documents),
        "tracker_name": tracker.name,
        "entries_count": len(
            tracker.document_entries or []
        ),
        "added_documents": added_documents,
        "sector": sector,
    }


def _normalize_sector(value):
    normalized = (value or "").strip().lower()

    mapping = {
        "railway": "Railways",
        "railways": "Railways",
        "defence": "Defence",
        "defense": "Defence",
        "private": "Private",
        "private sector": "Private",
        "others": "Others",
        "other": "Others",
        "commercial": "Others",
    }

    return mapping.get(normalized)


def _get_sector_for_sales_order(sales_order):
    source_sector = sales_order.get("custom_sector")

    if source_sector:
        resolved_sector = _normalize_sector(
            source_sector
        )

        if not resolved_sector:
            frappe.throw(
                _(
                    "Unable to map Sales Order sector '{0}' "
                    "to a PEPL Document Tracker sector."
                ).format(source_sector)
            )

        return resolved_sector

    customer_group = ""

    if sales_order.customer:
        customer_group = (
            frappe.db.get_value(
                "Customer",
                sales_order.customer,
                "customer_group",
            )
            or ""
        )

    return (
        _normalize_sector(customer_group)
        or "Others"
    )


def _get_sector_for_customer(customer):
    """
    Backward-compatible helper for any existing external callers.

    New Document Tracker creation must use
    _get_sector_for_sales_order().
    """
    if not customer:
        return "Others"

    customer_group = (
        frappe.db.get_value(
            "Customer",
            customer,
            "customer_group",
        )
        or ""
    )

    return (
        _normalize_sector(customer_group)
        or "Others"
    )


def _copy_tender_nda(
    tracker,
    source_tender,
    fallback_date,
):
    try:
        tender = frappe.get_doc(
            "PEPL Tender",
            source_tender,
        )

        nda_exists = any(
            row.document_type
            and "NDA" in row.document_type.upper()
            for row in tender.bid_documents or []
        )

        if not nda_exists:
            return

        tracker.append(
            "document_entries",
            {
                "document_date":
                    tender.bid_submission_deadline
                    or fallback_date,
                "document_type": "NDA",
                "description": "NDA carried from Tender",
                "direction": "Outbound (to Customer)",
                "document_status": "Filed",
                "source": "Auto-Copied from Tender",
                "source_reference": source_tender,
                "is_required": 0,
            },
        )

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "PEPL Document Tracker NDA Copy Failure",
        )
