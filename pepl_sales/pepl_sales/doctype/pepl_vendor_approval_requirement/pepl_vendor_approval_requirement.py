import frappe
from frappe import _
from frappe.model.document import Document


class PEPLVendorApprovalRequirement(Document):
    def validate(self):
        valid = {
            "Railways": {"Applied", "Developmental", "Approved"},
            "Defence": {"Developmental", "Established"},
            "Common": {"Applied", "Developmental", "Approved", "Established"},
        }
        if self.approval_stage not in valid.get(self.sector, set()):
            frappe.throw(_("Approval Stage {0} is not valid for Sector {1}.").format(self.approval_stage, self.sector))
        if self.sequence is not None and self.sequence < 0:
            frappe.throw(_("Sequence cannot be negative."))
