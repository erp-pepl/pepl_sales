import frappe
from frappe import _
from frappe.model.document import Document


class VendorApprovalDocument(Document):
    def validate(self):
        if self.document_type and self.document_type.startswith("---"):
            frappe.throw(_(
                "Please select an actual document type, not a section header."
            ))

        if self.document_source == "Company Library":
            if not self.linked_company_document:
                frappe.throw(_(
                    "Please pick a Company Document when source is 'Company Library'"
                ))
            company_doc = frappe.get_doc(
                "PEPL Company Document", self.linked_company_document
            )
            if company_doc.current_version_file:
                self.file_attach = company_doc.current_version_file
            if company_doc.current_issue_date:
                self.issue_date = company_doc.current_issue_date
            if company_doc.current_expiry_date:
                self.expiry_date = company_doc.current_expiry_date
            if company_doc.current_reference_no:
                self.reference_no = company_doc.current_reference_no
            if not self.document_type:
                self.document_type = (
                    company_doc.document_type
                    if company_doc.document_type != "Other"
                    else company_doc.name
                )

        elif self.document_source == "Item Drawing":
            if not self.linked_drawing_revision:
                frappe.throw(_(
                    "Please specify the drawing revision (e.g., A, B, C)"
                ))
            self._fetch_drawing_from_parent()

        elif self.document_source == "Item Specification":
            if not self.linked_specification:
                frappe.throw(_(
                    "Please specify the specification title"
                ))
            self._fetch_specification_from_parent()

        performance_doc_types = [
            "Inspection Certificate (Railways)",
            "Purchase Order (Railways)",
            "R-Note (Railways)",
            "Supply Order (Defence)",
            "I-Note (Defence)",
            "Customer Approval Email (Private)",
            "Customer Purchase Order (Private)"
        ]

        if self.document_type in performance_doc_types:
            if not self.customer:
                frappe.msgprint(
                    _("Performance document {0} typically needs Customer to be filled").format(
                        self.document_type
                    ),
                    indicator="orange",
                    alert=True
                )
            if not self.reference_no:
                frappe.msgprint(
                    _("Performance document {0} typically needs Reference Number").format(
                        self.document_type
                    ),
                    indicator="orange",
                    alert=True
                )

    def _fetch_drawing_from_parent(self):
        """Look up the drawing revision from parent Vendor Approval Status's Item."""
        if not self.parent or self.parenttype != "Vendor Approval Status":
            return

        parent_doc = frappe.get_doc("Vendor Approval Status", self.parent)
        if not parent_doc.item:
            return

        item_doc = frappe.get_doc("Item", parent_doc.item)
        drawings = getattr(item_doc, "custom_drawings", []) or []

        for d in drawings:
            if d.revision == self.linked_drawing_revision:
                if d.file_attach:
                    self.file_attach = d.file_attach
                if d.issue_date:
                    self.issue_date = d.issue_date
                self.document_name = f"Drawing Rev {d.revision}"
                return

        frappe.msgprint(
            _("Drawing revision '{0}' not found in Item {1}'s drawings table. Please add it there first.").format(
                self.linked_drawing_revision, parent_doc.item
            ),
            indicator="orange",
            alert=True
        )

    def _fetch_specification_from_parent(self):
        """Look up the specification from parent Vendor Approval Status's Item."""
        if not self.parent or self.parenttype != "Vendor Approval Status":
            return

        parent_doc = frappe.get_doc("Vendor Approval Status", self.parent)
        if not parent_doc.item:
            return

        item_doc = frappe.get_doc("Item", parent_doc.item)
        specifications = getattr(item_doc, "custom_specifications", []) or []

        for s in specifications:
            if s.spec_title == self.linked_specification:
                if s.file_attach:
                    self.file_attach = s.file_attach
                if s.issue_date:
                    self.issue_date = s.issue_date
                if s.reference_no:
                    self.reference_no = s.reference_no
                self.document_name = s.spec_title
                return

        frappe.msgprint(
            _("Specification '{0}' not found in Item {1}'s specifications table.").format(
                self.linked_specification, parent_doc.item
            ),
            indicator="orange",
            alert=True
        )
