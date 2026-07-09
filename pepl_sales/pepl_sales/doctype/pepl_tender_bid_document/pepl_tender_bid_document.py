import frappe
from frappe import _
from frappe.model.document import Document


class PEPLTenderBidDocument(Document):
    def validate(self):
        if self.document_source == "Company Library" and self.linked_company_document:
            company_doc = frappe.get_doc("PEPL Company Document", self.linked_company_document)
            if not self.document_type:
                self.document_type = (
                    company_doc.document_type
                    if company_doc.document_type != "Other"
                    else company_doc.name
                )
            if company_doc.current_version_file:
                self.file_attach = company_doc.current_version_file
            if not self.document_name:
                self.document_name = company_doc.name
