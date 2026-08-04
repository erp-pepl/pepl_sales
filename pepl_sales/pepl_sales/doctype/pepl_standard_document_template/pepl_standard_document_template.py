import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class PEPLStandardDocumentTemplate(Document):
    def validate(self):
        self._validate_effective_dates()
        self._validate_required_source_fields()
        self._validate_approved_template()
        self._apply_retired_state()

    def _validate_effective_dates(self):
        if (
            self.effective_from
            and self.effective_until
            and getdate(self.effective_until)
            < getdate(self.effective_from)
        ):
            frappe.throw(
                _(
                    "Effective Until cannot be earlier "
                    "than Effective From."
                )
            )

    def _validate_required_source_fields(self):
        try:
            fields = json.loads(
                self.required_source_fields
                or "[]"
            )
        except json.JSONDecodeError:
            frappe.throw(
                _(
                    "Required Source Fields must "
                    "contain valid JSON."
                )
            )

        if not isinstance(fields, list):
            frappe.throw(
                _(
                    "Required Source Fields must "
                    "be a JSON array."
                )
            )

        invalid_fields = [
            value
            for value in fields
            if not isinstance(value, str)
            or not value.strip()
        ]

        if invalid_fields:
            frappe.throw(
                _(
                    "Every Required Source Field "
                    "must be a non-empty string."
                )
            )

    def _validate_approved_template(self):
        if self.status != "Approved":
            return

        if (
            self.template_engine
            == "HTML Print"
            and not self.html_template
        ):
            frappe.throw(
                _(
                    "HTML Template is required "
                    "before approving an HTML "
                    "Print template."
                )
            )

        if (
            self.template_engine
            == "DOCX Template"
            and not self.source_template_file
        ):
            frappe.throw(
                _(
                    "Source Template File is "
                    "required before approving "
                    "a DOCX template."
                )
            )

        if not self.active:
            frappe.throw(
                _(
                    "An approved template must "
                    "be active."
                )
            )

        self.approved_by = (
            self.approved_by
            or frappe.session.user
        )
        self.approved_date = (
            self.approved_date
            or frappe.utils.today()
        )

    def _apply_retired_state(self):
        if self.status == "Retired":
            self.active = 0
