import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, today


class PEPLGeneratedDocument(Document):
    def before_insert(self):
        self.generated_by = (
            self.generated_by
            or frappe.session.user
        )
        self.generated_on = (
            self.generated_on
            or now_datetime()
        )

    def validate(self):
        self._validate_generation_context()
        self._apply_template_version()
        self._validate_unique_revision()
        self._calculate_source_data_hash()
        self._validate_issued_immutability()
        self._validate_lifecycle_status()

    def _validate_generation_context(self):
        try:
            context = json.loads(
                self.generation_context
                or "{}"
            )
        except json.JSONDecodeError:
            frappe.throw(
                _(
                    "Generation Context must "
                    "contain valid JSON."
                )
            )

        if not isinstance(context, dict):
            frappe.throw(
                _(
                    "Generation Context must "
                    "be a JSON object."
                )
            )

    def _apply_template_version(self):
        if not self.template:
            return

        self.template_version = (
            frappe.db.get_value(
                "PEPL Standard Document Template",
                self.template,
                "template_version",
            )
        )

    def _validate_unique_revision(self):
        if (
            not self.template
            or not self.source_doctype
            or not self.source_document
            or not self.revision_number
        ):
            return

        filters = {
            "template": self.template,
            "source_doctype": self.source_doctype,
            "source_document": self.source_document,
            "revision_number": self.revision_number,
        }

        existing = frappe.db.exists(
            "PEPL Generated Document",
            filters,
        )

        if existing and existing != self.name:
            frappe.throw(
                _(
                    "Revision {0} already exists for "
                    "template {1} and source document {2}."
                ).format(
                    self.revision_number,
                    self.template,
                    self.source_document,
                )
            )

    def _calculate_source_data_hash(self):
        payload = {
            "source_doctype":
                self.source_doctype,
            "source_document":
                self.source_document,
            "document_type":
                self.document_type,
            "template":
                self.template,
            "template_version":
                self.template_version,
            "revision_number":
                self.revision_number,
            "generation_context":
                self.generation_context or "{}",
        }

        self.source_data_hash = (
            hashlib.sha256(
                json.dumps(
                    payload,
                    sort_keys=True,
                    default=str,
                ).encode()
            ).hexdigest()
        )

    def _validate_issued_immutability(self):
        if self.is_new():
            return

        old_status = frappe.db.get_value(
            self.doctype,
            self.name,
            "status",
        )

        if old_status == "Issued":
            frappe.throw(
                _(
                    "An issued document is "
                    "immutable. Create a new "
                    "revision instead."
                )
            )

    def _validate_lifecycle_status(self):
        if (
            self.status in {
                "Reviewed",
                "Issued",
            }
            and not self.generated_file
        ):
            frappe.throw(
                _(
                    "Generated File is required "
                    "for status {0}."
                ).format(self.status)
            )

        if self.status == "Reviewed":
            if not self.reviewed_by:
                self.reviewed_by = (
                    frappe.session.user
                )

            if not self.reviewed_on:
                self.reviewed_on = (
                    now_datetime()
                )

        if self.status == "Issued":
            if not self.reviewed_by:
                frappe.throw(
                    _(
                        "Review the generated "
                        "document before issuing it."
                    )
                )

            self.issued_on = (
                self.issued_on
                or today()
            )

    @frappe.whitelist()
    def generate_pdf(self):
        """Generate or regenerate this draft document."""
        from pepl_sales.pepl_sales.api.standard_document_generation import (
            generate_pdf,
        )

        if self.is_new():
            frappe.throw(
                _(
                    "Save the Generated Document "
                    "before generating its PDF."
                )
            )

        return generate_pdf(
            self.name
        )

    @frappe.whitelist()
    def create_revision(self):
        """Create the next controlled revision."""
        from pepl_sales.pepl_sales.api.standard_document_generation import (
            create_revision,
        )

        if self.is_new():
            frappe.throw(
                _(
                    "Save the Generated Document "
                    "before creating a revision."
                )
            )

        return create_revision(
            self.name
        )


@frappe.whitelist()
def generate_pdf(docname):
    """
    Whitelisted module-level wrapper used by the form button.

    Frappe resolves dotted RPC paths against module-level functions,
    therefore this wrapper loads the document and delegates to the
    permanent controller method.
    """
    if not docname:
        frappe.throw(_("Generated Document is required."))

    doc = frappe.get_doc(
        "PEPL Generated Document",
        docname,
    )
    doc.check_permission("write")

    return doc.run_method(
        "generate_pdf"
    )


@frappe.whitelist()
def create_revision(docname):
    """
    Whitelisted module-level wrapper used by the form button.
    """
    if not docname:
        frappe.throw(_("Generated Document is required."))

    doc = frappe.get_doc(
        "PEPL Generated Document",
        docname,
    )
    doc.check_permission("read")

    return doc.run_method(
        "create_revision"
    )
