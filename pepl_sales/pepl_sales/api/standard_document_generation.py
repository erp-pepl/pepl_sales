from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate, nowdate
from frappe.utils.file_manager import save_file
from frappe.utils.pdf import get_pdf


SUPPORTED_SOURCE_DOCTYPES = {
    "PEPL Tender",
    "Sales Order",
    "Sales Invoice",
    "PEPL PSD Tracker",
    "PEPL Document Tracker",
}


def _clean_filename(value):
    value = re.sub(
        r'[\\/:*?"<>|]+',
        "_",
        value or "",
    )
    value = re.sub(
        r"\s+",
        "_",
        value,
    )
    value = value.strip("._")

    return value or "PEPL_Document"


def _get_nested_value(data, field_path):
    current = data

    for part in field_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    return current


def _get_customer_primary_address(customer):
    if not customer:
        return None

    links = frappe.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Customer",
            "link_name": customer,
            "parenttype": "Address",
        },
        fields=["parent"],
        limit_page_length=100,
    )

    address_names = []

    for link in links:
        if link.parent not in address_names:
            address_names.append(link.parent)

    if not address_names:
        return None

    addresses = frappe.get_all(
        "Address",
        filters={
            "name": ["in", address_names],
            "disabled": 0,
        },
        fields=[
            "name",
            "is_primary_address",
            "is_shipping_address",
            "modified",
        ],
        order_by=(
            "is_primary_address desc, "
            "is_shipping_address desc, "
            "modified desc"
        ),
        limit_page_length=100,
    )

    if not addresses:
        return None

    return frappe.get_doc(
        "Address",
        addresses[0].name,
    ).as_dict()


def _get_selected_psd_entry(
    source_doc,
    psd_entry_row=None,
):
    entries = (
        source_doc.get("psd_entries")
        or []
    )

    if psd_entry_row:
        for entry in entries:
            if entry.name == psd_entry_row:
                return entry.as_dict()

        frappe.throw(
            _(
                "PSD Entry Row {0} was not found "
                "in PSD Tracker {1}."
            ).format(
                psd_entry_row,
                source_doc.name,
            )
        )

    if len(entries) == 1:
        return entries[0].as_dict()

    if len(entries) > 1:
        frappe.throw(
            _(
                "PSD Tracker {0} has multiple "
                "PSD entries. Select the required "
                "PSD Entry Row."
            ).format(source_doc.name)
        )

    return None


def _get_source_context(source_doc, psd_entry_row=None):
    context = {
        "doc": source_doc.as_dict(),
        "source_doctype": source_doc.doctype,
        "source_document": source_doc.name,
        "today": nowdate(),
    }

    for fieldname in [
        "customer",
        "sector",
        "company",
        "currency",
    ]:
        if source_doc.meta.has_field(fieldname):
            context[fieldname] = source_doc.get(
                fieldname
            )

    if source_doc.doctype == "Sales Order":
        context["sales_order"] = (
            source_doc.as_dict()
        )

    elif source_doc.doctype == "Sales Invoice":
        context["sales_invoice"] = (
            source_doc.as_dict()
        )

    elif source_doc.doctype == "PEPL Tender":
        context["tender"] = (
            source_doc.as_dict()
        )

    elif source_doc.doctype == "PEPL PSD Tracker":
        context["psd_tracker"] = (
            source_doc.as_dict()
        )

        selected_psd_entry = (
            _get_selected_psd_entry(
                source_doc,
                psd_entry_row=psd_entry_row,
            )
        )

        context["selected_psd_entry"] = (
            selected_psd_entry
        )

        sales_order_name = (
            source_doc.get(
                "linked_sales_order"
            )
            or source_doc.get(
                "sales_order"
            )
        )

        if sales_order_name:
            sales_order = frappe.get_doc(
                "Sales Order",
                sales_order_name,
            )

            context["sales_order"] = (
                sales_order.as_dict()
            )

            customer_name = (
                sales_order.customer
                or source_doc.get("customer")
            )

            if customer_name:
                customer_doc = frappe.get_doc(
                    "Customer",
                    customer_name,
                )

                context["customer_doc"] = (
                    customer_doc.as_dict()
                )

                context["customer_address"] = (
                    _get_customer_primary_address(
                        customer_name
                    )
                )

            if sales_order.company:
                company_doc = frappe.get_doc(
                    "Company",
                    sales_order.company,
                )

                context["company_doc"] = (
                    company_doc.as_dict()
                )

    elif (
        source_doc.doctype
        == "PEPL Document Tracker"
    ):
        context["document_tracker"] = (
            source_doc.as_dict()
        )

    return context


def _validate_required_fields(
    template,
    context,
):
    required_fields = frappe.parse_json(
        template.required_source_fields
        or "[]"
    )

    missing = []

    for field_path in required_fields:
        clean_path = field_path.strip()

        if clean_path.startswith("doc."):
            lookup_path = clean_path[4:]
            value = _get_nested_value(
                context.get("doc", {}),
                lookup_path,
            )
        else:
            value = _get_nested_value(
                context,
                clean_path,
            )

        if value in (
            None,
            "",
            [],
            {},
        ):
            missing.append(clean_path)

    if missing:
        frappe.throw(
            _(
                "The following required source "
                "fields are missing: {0}"
            ).format(
                ", ".join(missing)
            )
        )


def _get_source_customer(source_doc):
    for fieldname in [
        "customer",
        "party_name",
    ]:
        if (
            source_doc.meta.has_field(fieldname)
            and source_doc.get(fieldname)
        ):
            return source_doc.get(fieldname)

    return None


def _get_source_sector(source_doc):
    if (
        source_doc.meta.has_field("sector")
        and source_doc.get("sector")
    ):
        return source_doc.get("sector")

    customer = _get_source_customer(
        source_doc
    )

    if not customer:
        return "Common"

    customer_group = frappe.db.get_value(
        "Customer",
        customer,
        "customer_group",
    ) or ""

    if "Railway" in customer_group:
        return "Railways"

    if "Defence" in customer_group:
        return "Defence"

    if "Private" in customer_group:
        return "Private"

    return "Others"


def _set_related_links(
    generated_doc,
    source_doc,
):
    if source_doc.doctype == "PEPL Tender":
        generated_doc.tender = source_doc.name

    elif source_doc.doctype == "Sales Order":
        generated_doc.sales_order = (
            source_doc.name
        )

    elif source_doc.doctype == "Sales Invoice":
        generated_doc.sales_invoice = (
            source_doc.name
        )

    elif (
        source_doc.doctype
        == "PEPL PSD Tracker"
    ):
        generated_doc.psd_tracker = (
            source_doc.name
        )

        linked_sales_order = (
            source_doc.get(
                "linked_sales_order"
            )
            or source_doc.get(
                "sales_order"
            )
        )

        if linked_sales_order:
            generated_doc.sales_order = (
                linked_sales_order
            )

    elif (
        source_doc.doctype
        == "PEPL Document Tracker"
    ):
        generated_doc.document_tracker = (
            source_doc.name
        )

        linked_sales_order = (
            source_doc.get(
                "linked_sales_order"
            )
            or source_doc.get(
                "sales_order"
            )
        )

        if linked_sales_order:
            generated_doc.sales_order = (
                linked_sales_order
            )


@frappe.whitelist()
def get_applicable_templates(
    source_doctype,
    source_document,
    document_type=None,
):
    if (
        source_doctype
        not in SUPPORTED_SOURCE_DOCTYPES
    ):
        frappe.throw(
            _(
                "Unsupported source DocType: {0}"
            ).format(source_doctype)
        )

    source_doc = frappe.get_doc(
        source_doctype,
        source_document,
    )
    source_doc.check_permission("read")

    customer = _get_source_customer(
        source_doc
    )
    sector = _get_source_sector(
        source_doc
    )

    filters = {
        "active": 1,
        "status": "Approved",
        "template_engine": "HTML Print",
        "sector": [
            "in",
            [
                "Common",
                sector,
            ],
        ],
    }

    if document_type:
        filters["document_requirement"] = (
            document_type
        )

    templates = frappe.get_all(
        "PEPL Standard Document Template",
        filters=filters,
        fields=[
            "name",
            "template_code",
            "template_name",
            "document_requirement",
            "sector",
            "customer",
            "output_format",
            "template_version",
            "requires_manual_review",
            "requires_signature",
            "requires_stamp",
        ],
        order_by=(
            "customer desc, "
            "sector desc, "
            "template_name asc"
        ),
        limit_page_length=500,
    )

    applicable = []

    for template in templates:
        if (
            template.customer
            and template.customer != customer
        ):
            continue

        applicable.append(template)

    return applicable


@frappe.whitelist()
def create_generated_document(
    template_name,
    source_doctype,
    source_document,
    psd_entry_row=None,
):
    if (
        source_doctype
        not in SUPPORTED_SOURCE_DOCTYPES
    ):
        frappe.throw(
            _(
                "Unsupported source DocType: {0}"
            ).format(source_doctype)
        )

    template = frappe.get_doc(
        "PEPL Standard Document Template",
        template_name,
    )
    template.check_permission("read")

    if not template.active:
        frappe.throw(
            _("The selected template is inactive.")
        )

    if template.status != "Approved":
        frappe.throw(
            _(
                "Only approved templates can "
                "generate documents."
            )
        )

    if template.template_engine != "HTML Print":
        frappe.throw(
            _(
                "This phase supports HTML Print "
                "templates only."
            )
        )

    source_doc = frappe.get_doc(
        source_doctype,
        source_document,
    )
    source_doc.check_permission("read")

    context = _get_source_context(
        source_doc,
        psd_entry_row=psd_entry_row,
    )

    _validate_required_fields(
        template,
        context,
    )

    previous_documents = frappe.get_all(
        "PEPL Generated Document",
        filters={
            "template": template.name,
            "source_doctype": source_doctype,
            "source_document": source_document,
        },
        fields=[
            "name",
            "revision_number",
        ],
        order_by=(
            "revision_number desc, "
            "creation desc"
        ),
        limit_page_length=1,
    )

    previous_revision = (
        previous_documents[0].revision_number
        if previous_documents
        else 0
    )

    revision_number = (
        int(previous_revision or 0)
        + 1
    )

    generated_doc = frappe.new_doc(
        "PEPL Generated Document"
    )
    generated_doc.document_type = (
        template.document_requirement
    )
    generated_doc.template = template.name
    generated_doc.source_doctype = (
        source_doctype
    )
    generated_doc.source_document = (
        source_document
    )
    generated_doc.customer = (
        _get_source_customer(
            source_doc
        )
    )
    generated_doc.sector = (
        _get_source_sector(
            source_doc
        )
    )
    generated_doc.revision_number = (
        revision_number
    )
    generated_doc.status = "Draft"
    generated_doc.generation_context = (
        json.dumps(
            context,
            default=str,
            sort_keys=True,
        )
    )

    _set_related_links(
        generated_doc,
        source_doc,
    )

    if (
        source_doctype
        == "PEPL PSD Tracker"
    ):
        generated_doc.psd_entry_row = (
            psd_entry_row
            or (
                context.get(
                    "selected_psd_entry"
                )
                or {}
            ).get("name")
        )

    generated_doc.insert()

    return {
        "generated_document":
            generated_doc.name,
        "revision_number":
            generated_doc.revision_number,
    }


@frappe.whitelist()
def generate_pdf(
    generated_document_name,
):
    generated_doc = frappe.get_doc(
        "PEPL Generated Document",
        generated_document_name,
    )
    generated_doc.check_permission("write")

    if generated_doc.status == "Issued":
        frappe.throw(
            _(
                "An issued document cannot "
                "be regenerated. Create a "
                "new revision."
            )
        )

    template = frappe.get_doc(
        "PEPL Standard Document Template",
        generated_doc.template,
    )

    if not template.active:
        frappe.throw(
            _("The selected template is inactive.")
        )

    if template.status != "Approved":
        frappe.throw(
            _(
                "The selected template is "
                "not approved."
            )
        )

    if template.template_engine != "HTML Print":
        frappe.throw(
            _(
                "PDF generation currently "
                "supports HTML Print templates."
            )
        )

    if not template.html_template:
        frappe.throw(
            _(
                "The selected template has "
                "no HTML content."
            )
        )

    source_doc = frappe.get_doc(
        generated_doc.source_doctype,
        generated_doc.source_document,
    )

    context = _get_source_context(
        source_doc,
        psd_entry_row=(
            generated_doc.psd_entry_row
        ),
    )

    context["generated_document"] = (
        generated_doc.as_dict()
    )
    context["template"] = (
        template.as_dict()
    )
    context["revision"] = (
        generated_doc.revision_number
    )

    _validate_required_fields(
        template,
        context,
    )

    try:
        rendered_html = frappe.render_template(
            template.html_template,
            context,
        )

        audit_footer = frappe.render_template(
            """
            <div style="
                margin-top: 24px;
                padding-top: 8px;
                border-top: 1px solid #999;
                font-family: Arial, sans-serif;
                font-size: 8px;
                color: #666;
                text-align: center;
            ">
                Controlled Document:
                {{ generated_document.name }}
                |
                Template:
                {{ template.template_code }}
                v{{ template.template_version }}
                |
                Revision:
                {{ revision }}
                |
                Source:
                {{ source_doctype }}
                {{ source_document }}
                |
                Generated:
                {{ generated_document.generated_on }}
            </div>
            """,
            context,
        )

        rendered_html = (
            rendered_html
            + audit_footer
        )

        pdf_content = get_pdf(
            rendered_html
        )

        filename_pattern = (
            template.output_filename_pattern
            or (
                template.template_code
                + "_{{ source_document }}"
                + "_R{{ revision }}.pdf"
            )
        )

        rendered_filename = (
            frappe.render_template(
                filename_pattern,
                context,
            )
        )

        if not rendered_filename.lower().endswith(
            ".pdf"
        ):
            rendered_filename += ".pdf"

        filename = _clean_filename(
            rendered_filename[:-4]
        ) + ".pdf"

        previous_file_url = (
            generated_doc.generated_file
        )

        file_doc = save_file(
            filename,
            pdf_content,
            generated_doc.doctype,
            generated_doc.name,
            is_private=1,
        )

        generated_doc.generated_file = (
            file_doc.file_url
        )
        generated_doc.generation_context = (
            json.dumps(
                context,
                default=str,
                sort_keys=True,
            )
        )
        generated_doc.error_log = None
        generated_doc.save()

        duplicate_file_rows = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype":
                    generated_doc.doctype,
                "attached_to_name":
                    generated_doc.name,
                "file_url":
                    generated_doc.generated_file,
            },
            fields=[
                "name",
                "creation",
            ],
            order_by="creation desc",
            limit_page_length=100,
        )

        for duplicate_file in duplicate_file_rows:
            if duplicate_file.name == file_doc.name:
                continue

            frappe.delete_doc(
                "File",
                duplicate_file.name,
                ignore_permissions=True,
            )

        if (
            previous_file_url
            and previous_file_url
            != generated_doc.generated_file
        ):
            previous_file_name = (
                frappe.db.get_value(
                    "File",
                    {
                        "file_url":
                            previous_file_url,
                        "attached_to_doctype":
                            generated_doc.doctype,
                        "attached_to_name":
                            generated_doc.name,
                    },
                    "name",
                )
            )

            if previous_file_name:
                frappe.delete_doc(
                    "File",
                    previous_file_name,
                    ignore_permissions=True,
                )

        return {
            "generated_document":
                generated_doc.name,
            "generated_file":
                generated_doc.generated_file,
            "filename":
                filename,
        }

    except Exception:
        error = frappe.get_traceback()

        generated_doc.db_set(
            "error_log",
            error,
            update_modified=False,
        )

        frappe.log_error(
            error,
            (
                "PEPL Standard Document "
                "Generation"
            ),
        )

        frappe.throw(
            _(
                "Document generation failed. "
                "The technical error has been logged."
            )
        )


@frappe.whitelist()
def create_revision(
    generated_document_name,
):
    source_doc = frappe.get_doc(
        "PEPL Generated Document",
        generated_document_name,
    )
    source_doc.check_permission("read")

    return create_generated_document(
        template_name=source_doc.template,
        source_doctype=(
            source_doc.source_doctype
        ),
        source_document=(
            source_doc.source_document
        ),
        psd_entry_row=(
            source_doc.psd_entry_row
        ),
    )


@frappe.whitelist()
def get_renderer_deployment_info():
    return {
        "component": "standard_document_generation",
        "revision_query": "ordered_get_all",
        "unique_revision_validation": True,
        "release_marker": "e049511-revision-sequencing",
    }


@frappe.whitelist()
def create_from_psd_tracker(
    tracker_name,
    template_name,
    psd_entry_row,
):
    if not tracker_name:
        frappe.throw(
            _("PSD Tracker is required.")
        )

    if not template_name:
        frappe.throw(
            _("Document Template is required.")
        )

    if not psd_entry_row:
        frappe.throw(
            _("PSD Entry Row is required.")
        )

    tracker = frappe.get_doc(
        "PEPL PSD Tracker",
        tracker_name,
    )

    tracker.check_permission("read")

    selected_entry = None

    for row in tracker.get(
        "psd_entries"
    ) or []:
        if row.name == psd_entry_row:
            selected_entry = row
            break

    if not selected_entry:
        frappe.throw(
            _(
                "PSD Entry Row {0} does not belong "
                "to PSD Tracker {1}."
            ).format(
                psd_entry_row,
                tracker.name,
            )
        )

    template = frappe.get_doc(
        "PEPL Standard Document Template",
        template_name,
    )

    if not template.active:
        frappe.throw(
            _("The selected template is inactive.")
        )

    if template.status != "Approved":
        frappe.throw(
            _("The selected template is not approved.")
        )

    return create_generated_document(
        template_name=template.name,
        source_doctype="PEPL PSD Tracker",
        source_document=tracker.name,
        psd_entry_row=selected_entry.name,
    )
