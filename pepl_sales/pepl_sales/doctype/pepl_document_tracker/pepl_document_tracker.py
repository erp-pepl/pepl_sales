import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


RECEIVED_STATUSES = {"Received", "Filed"}


class PEPLDocumentTracker(Document):
    def validate(self):
        self.total_documents = len(self.document_entries or [])

        if not self.tracker_id:
            self.tracker_id = self.name

        self._validate_document_entries()

    def _validate_document_entries(self):
        for index, row in enumerate(
            self.document_entries or [],
            start=1,
        ):
            if row.document_status in RECEIVED_STATUSES:
                if not row.received_date:
                    row.received_date = today()

                if not row.received_by:
                    row.received_by = frappe.session.user

            if (
                row.document_type == "Material Receipt"
                and row.document_status in RECEIVED_STATUSES
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

            if row.document_status == "Pending":
                row.received_date = None
                row.received_by = None


@frappe.whitelist()
def create_doc_tracker_for_so(
    sales_order_name,
    source_tender=None,
):
    existing = frappe.db.exists(
        "PEPL Document Tracker",
        {"linked_sales_order": sales_order_name},
    )

    if existing:
        return {
            "created": False,
            "tracker_name": existing,
        }

    sales_order = frappe.get_doc(
        "Sales Order",
        sales_order_name,
    )

    tracker = frappe.new_doc("PEPL Document Tracker")
    tracker.linked_sales_order = sales_order.name
    tracker.customer = sales_order.customer

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
            "source": "Auto-Generated",
            "is_required": 1,
        },
    )

    sector = _get_sector_for_customer(
        sales_order.customer
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
                "source": "Auto-Generated",
                "is_required": 1,
            },
        )

    if source_tender:
        _copy_tender_nda(
            tracker,
            source_tender,
            sales_order.transaction_date,
        )

    tracker.insert(ignore_permissions=True)

    return {
        "created": True,
        "tracker_name": tracker.name,
        "entries_count": len(
            tracker.document_entries or []
        ),
        "sector": sector,
    }


def _get_sector_for_customer(customer):
    if not customer:
        return "Others"

    customer_group = frappe.db.get_value(
        "Customer",
        customer,
        "customer_group",
    ) or ""

    if "Railway" in customer_group:
        return "Railways"

    if "Defence" in customer_group:
        return "Defence"

    if "Private" in customer_group:
        return "Private"

    return "Others"


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
