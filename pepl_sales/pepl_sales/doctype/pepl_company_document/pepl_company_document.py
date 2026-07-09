import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class PEPLCompanyDocument(Document):
    def validate(self):
        if self.document_type == "Other" and not self.document_type_other:
            frappe.throw(_(
                "When Document Type is 'Other', please specify what document this is"
            ))

        if self.document_type == "Other" and self.document_type_other:
            if self.is_new():
                proposed_name = self.document_type_other.strip()
                if frappe.db.exists("PEPL Company Document", proposed_name):
                    frappe.throw(_(
                        "A document with name '{0}' already exists. Please use a different name."
                    ).format(proposed_name))
                self.name = proposed_name

        if self.document_type and self.document_type != "Other":
            existing = frappe.db.exists(
                "PEPL Company Document",
                {"document_type": self.document_type, "name": ["!=", self.name]}
            )
            if existing:
                frappe.throw(_(
                    "A {0} document already exists. Please update the existing one rather than creating a duplicate."
                ).format(self.document_type))

        if not self.versions:
            frappe.throw(_("At least one version must be added"))

        current_versions = [v for v in self.versions if v.is_current]

        if len(current_versions) == 0:
            sorted_versions = sorted(
                self.versions,
                key=lambda v: getdate(v.issue_date) if v.issue_date else getdate("1900-01-01"),
                reverse=True
            )
            sorted_versions[0].is_current = 1
            current_versions = [sorted_versions[0]]
            frappe.msgprint(
                _("Auto-marked the most recent version as current. You can change this manually if needed."),
                indicator="blue",
                alert=True
            )

        if len(current_versions) > 1:
            frappe.throw(_(
                "Only one version can be marked as 'Current Version'. "
                "Please untick the others."
            ))

        current = current_versions[0]
        if current.expiry_date and getdate(current.expiry_date) < getdate(today()):
            frappe.msgprint(
                _("Current version of {0} expired on {1}. Please add a renewed version.").format(
                    self.document_type, current.expiry_date
                ),
                indicator="red",
                alert=True
            )

        self.current_version_file = current.file_attach
        self.current_version_number = current.version_number
        self.current_issue_date = current.issue_date
        self.current_expiry_date = current.expiry_date
        self.current_reference_no = current.reference_no


@frappe.whitelist()
def get_current_document(document_type):
    """Returns the current version file of a Company Document.
    Used by Vendor Approval Status, Tender Management to fetch
    the latest file without duplication."""

    doc = frappe.db.get_value(
        "PEPL Company Document",
        {"document_type": document_type, "is_active": 1},
        ["name", "current_version_file", "current_issue_date",
         "current_expiry_date", "current_reference_no", "current_version_number"],
        as_dict=True
    )

    if not doc:
        return None

    is_expired = False
    if doc.current_expiry_date:
        if getdate(doc.current_expiry_date) < getdate(today()):
            is_expired = True

    return {
        "exists": True,
        "name": doc.name,
        "file": doc.current_version_file,
        "version": doc.current_version_number,
        "issue_date": doc.current_issue_date,
        "expiry_date": doc.current_expiry_date,
        "reference_no": doc.current_reference_no,
        "is_expired": is_expired
    }


@frappe.whitelist()
def list_active_documents():
    """Returns list of all active Company Documents for dropdown selection."""

    docs = frappe.get_all(
        "PEPL Company Document",
        filters={"is_active": 1},
        fields=["name", "document_type", "document_type_other", "category"],
        order_by="document_type asc"
    )

    return docs
