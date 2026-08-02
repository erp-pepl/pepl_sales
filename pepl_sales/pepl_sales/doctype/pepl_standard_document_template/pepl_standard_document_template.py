import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class PEPLStandardDocumentTemplate(Document):
    def validate(self):
        if self.effective_from and self.effective_until and getdate(self.effective_until) < getdate(self.effective_from):
            frappe.throw(_("Effective Until cannot be earlier than Effective From."))
        try:
            fields = json.loads(self.required_source_fields or "[]")
        except json.JSONDecodeError:
            frappe.throw(_("Required Source Fields must contain valid JSON."))
        if not isinstance(fields, list):
            frappe.throw(_("Required Source Fields must be a JSON array."))
        if self.status == "Approved":
            if not self.source_template_file:
                frappe.throw(_("Source Template File is required before approval."))
            self.approved_by = self.approved_by or frappe.session.user
            self.approved_date = self.approved_date or frappe.utils.today()
        if self.status == "Retired":
            self.active = 0
