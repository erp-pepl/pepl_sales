import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, today


class PEPLGeneratedDocument(Document):
    def before_insert(self):
        self.generated_by = frappe.session.user
        self.generated_on = now_datetime()

    def validate(self):
        try:
            context = json.loads(self.generation_context or "{}")
        except json.JSONDecodeError:
            frappe.throw(_("Generation Context must contain valid JSON."))
        if not isinstance(context, dict):
            frappe.throw(_("Generation Context must be a JSON object."))

        if self.template:
            self.template_version = frappe.db.get_value("PEPL Standard Document Template", self.template, "template_version")

        payload = {
            "source_doctype": self.source_doctype,
            "source_document": self.source_document,
            "document_type": self.document_type,
            "template": self.template,
            "template_version": self.template_version,
            "revision_number": self.revision_number,
            "generation_context": self.generation_context or "{}",
        }
        self.source_data_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

        old_status = None if self.is_new() else frappe.db.get_value(self.doctype, self.name, "status")
        if old_status == "Issued":
            frappe.throw(_("An issued document is immutable. Create a new revision instead."))
        if self.status in {"Reviewed", "Issued"} and not self.generated_file:
            frappe.throw(_("Generated File is required for status {0}.").format(self.status))
        if self.status == "Reviewed" and not self.reviewed_by:
            self.reviewed_by = frappe.session.user
            self.reviewed_on = now_datetime()
        if self.status == "Issued":
            if not self.reviewed_by:
                frappe.throw(_("Review the generated document before issuing it."))
            self.issued_on = self.issued_on or today()
