import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


COMPLETED_DOCUMENT_STATUSES = {
    "Received",
    "Filed",
}


def validate_document_entry(doc, row_number=None):
    """
    Validate chronology and status consistency for one Document Entry.

    This function is intentionally callable from both:
        - PEPL Document Entry.validate()
        - PEPL Document Tracker.validate()

    Child-table validate hooks are not sufficient by themselves when the
    parent document is saved, so the parent must invoke this function.
    """
    row_label = (
        _("Document row {0}").format(row_number)
        if row_number
        else _("Document Entry")
    )

    if not doc.document_status:
        frappe.throw(
            _(
                "{0}: Document Status is required."
            ).format(row_label)
        )

    if doc.received_date and not doc.document_date:
        frappe.throw(
            _(
                "{0}: Document Date is required when "
                "Received Date is entered."
            ).format(row_label)
        )

    if (
        doc.document_date
        and doc.received_date
        and getdate(doc.received_date)
        < getdate(doc.document_date)
    ):
        frappe.throw(
            _(
                "{0}: Received Date {1} cannot be earlier "
                "than Document Date {2}."
            ).format(
                row_label,
                doc.received_date,
                doc.document_date,
            )
        )

    if doc.document_status == "Pending":
        if doc.received_date:
            frappe.throw(
                _(
                    "{0}: Pending documents cannot have "
                    "a Received Date."
                ).format(row_label)
            )

        if doc.received_by:
            frappe.throw(
                _(
                    "{0}: Pending documents cannot have "
                    "a Received By user."
                ).format(row_label)
            )

    if doc.document_status in COMPLETED_DOCUMENT_STATUSES:
        if not doc.document_date:
            frappe.throw(
                _(
                    "{0}: Document Date is required when "
                    "Status is {1}."
                ).format(
                    row_label,
                    doc.document_status,
                )
            )

        if not doc.received_date:
            frappe.throw(
                _(
                    "{0}: Received Date is required when "
                    "Status is {1}."
                ).format(
                    row_label,
                    doc.document_status,
                )
            )

        if not doc.received_by:
            frappe.throw(
                _(
                    "{0}: Received By is required when "
                    "Status is {1}."
                ).format(
                    row_label,
                    doc.document_status,
                )
            )


class PEPLDocumentEntry(Document):
    def validate(self):
        validate_document_entry(self)
