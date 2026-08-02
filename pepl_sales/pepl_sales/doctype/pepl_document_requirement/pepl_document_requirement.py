import frappe
from frappe import _
from frappe.model.document import Document


class PEPLDocumentRequirement(Document):
    def validate(self):
        if self.generated_by_pepl and self.external_issued:
            frappe.throw(_("A document cannot be both PEPL-generated and customer/bank-issued."))
        if self.external_issued:
            self.evidence_required = 1
        if self.sequence is not None and self.sequence < 0:
            frappe.throw(_("Sequence cannot be negative."))
