import frappe
from frappe import _
from frappe.model.document import Document


class PEPLDocumentTracker(Document):
    def validate(self):
        self.total_documents = len(self.document_entries) if self.document_entries else 0

        if not self.tracker_id:
            self.tracker_id = self.name


@frappe.whitelist()
def create_doc_tracker_for_so(sales_order_name, source_tender=None):
    """Create one Document Tracker per Sales Order with default Customer PO entry.
    Idempotent — returns existing tracker if already created.
    """
    existing = frappe.db.exists("PEPL Document Tracker", {"linked_sales_order": sales_order_name})
    if existing:
        return {"created": False, "tracker_name": existing}

    so = frappe.get_doc("Sales Order", sales_order_name)

    tracker = frappe.new_doc("PEPL Document Tracker")
    tracker.linked_sales_order = so.name
    tracker.customer = so.customer

    po_title = f"Customer PO {so.po_no}" if so.po_no else "Customer PO"
    tracker.append("document_entries", {
        "document_date": so.po_date or so.transaction_date,
        "document_type": "Customer PO",
        "description": po_title,
        "reference_number": so.po_no or "",
        "direction": "Inbound (from Customer)",
        "document_status": "Received",
        "source": "Auto-Generated"
    })

    if source_tender:
        try:
            tender = frappe.get_doc("PEPL Tender", source_tender)
            for bid_doc in (tender.bid_documents or []):
                if bid_doc.document_type and "NDA" in bid_doc.document_type.upper():
                    tracker.append("document_entries", {
                        "document_date": tender.bid_submission_deadline or so.transaction_date,
                        "document_type": "NDA",
                        "description": "NDA (carried from Tender)",
                        "direction": "Outbound (to Customer)",
                        "document_status": "Filed",
                        "source": "Auto-Copied from Tender",
                        "source_reference": source_tender
                    })
                    break
        except Exception as e:
            frappe.log_error(f"Failed to copy tender NDA: {str(e)}", "Module 5 Doc Tracker")

    tracker.insert(ignore_permissions=True)

    return {
        "created": True,
        "tracker_name": tracker.name,
        "entries_count": len(tracker.document_entries)
    }
