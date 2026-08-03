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
        """Fetch a drawing from the linked PEPL Product Master."""
        if (
            not self.parent
            or self.parenttype != "Vendor Approval Status"
        ):
            return

        parent_doc = frappe.get_doc(
            "Vendor Approval Status",
            self.parent,
        )

        if not parent_doc.item:
            return

        product_name = frappe.db.get_value(
            "PEPL Product Master",
            {
                "linked_item": parent_doc.item,
                "status": "Active",
            },
            "name",
        )

        if not product_name:
            return

        product = frappe.get_doc(
            "PEPL Product Master",
            product_name,
        )

        for drawing in product.drawing_revisions or []:
            if (
                drawing.revision
                != self.linked_drawing_revision
            ):
                continue

            if drawing.drawing_file:
                self.file_attach = (
                    drawing.drawing_file
                )

            if drawing.issue_date:
                self.issue_date = drawing.issue_date

            if not self.reference_no:
                self.reference_no = (
                    product.drawing_number
                    or drawing.revision
                )

            return

    def _fetch_specification_from_parent(self):
        """Fetch a specification from PEPL Product Master."""
        if (
            not self.parent
            or self.parenttype != "Vendor Approval Status"
        ):
            return

        parent_doc = frappe.get_doc(
            "Vendor Approval Status",
            self.parent,
        )

        if not parent_doc.item:
            return

        product_name = frappe.db.get_value(
            "PEPL Product Master",
            {
                "linked_item": parent_doc.item,
                "status": "Active",
            },
            "name",
        )

        if not product_name:
            return

        product = frappe.get_doc(
            "PEPL Product Master",
            product_name,
        )

        for specification in product.specifications or []:
            if (
                specification.spec_title
                != self.linked_specification
            ):
                continue

            if specification.spec_file:
                self.file_attach = (
                    specification.spec_file
                )

            if specification.issue_date:
                self.issue_date = (
                    specification.issue_date
                )

            if specification.reference_no:
                self.reference_no = (
                    specification.reference_no
                )

            return
