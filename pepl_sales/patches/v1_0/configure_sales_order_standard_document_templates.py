import json

import frappe


BASE_STYLE = """
<style>
    body {
        font-family: Arial, sans-serif;
        font-size: 11px;
        line-height: 1.5;
        color: #111;
    }

    .pepl-document {
        padding: 18px 26px;
    }

    .pepl-header {
        text-align: center;
        border-bottom: 1px solid #555;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }

    .pepl-company {
        font-size: 17px;
        font-weight: 700;
    }

    .pepl-title {
        margin-top: 5px;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
    }

    .pepl-meta,
    .pepl-items {
        width: 100%;
        border-collapse: collapse;
    }

    .pepl-meta {
        margin-bottom: 18px;
    }

    .pepl-meta td {
        padding: 3px 0;
        vertical-align: top;
    }

    .pepl-items {
        margin: 16px 0;
    }

    .pepl-items th,
    .pepl-items td {
        border: 1px solid #777;
        padding: 6px;
        vertical-align: top;
    }

    .pepl-items th {
        background: #f2f2f2;
        text-align: left;
    }

    .pepl-signature {
        margin-top: 42px;
    }

    .pepl-note {
        margin-top: 20px;
        padding: 8px;
        border: 1px solid #999;
        font-size: 9px;
        color: #555;
    }

    .pepl-label {
        border: 2px solid #222;
        padding: 14px;
        margin-bottom: 12px;
        page-break-inside: avoid;
    }
</style>
"""


COMMON_REQUIRED_FIELDS = [
    "source_doctype",
    "source_document",
    "customer",
    "sales_order.name",
    "sales_order.customer",
    "sales_order.transaction_date",
    "sales_order.company",
    "sales_order.items",
]


ITEM_TABLE = """
<table class="pepl-items">
    <thead>
        <tr>
            <th style="width: 6%;">Sl.</th>
            <th style="width: 18%;">Item Code</th>
            <th>Description</th>
            <th style="width: 12%;">Quantity</th>
            <th style="width: 10%;">UOM</th>
            <th style="width: 14%;">Delivery Date</th>
        </tr>
    </thead>
    <tbody>
        {% for item in sales_order.items or [] %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ item.item_code or "-" }}</td>
            <td>
                {{
                    item.description
                    or item.item_name
                    or "-"
                }}
            </td>
            <td>{{ item.qty or 0 }}</td>
            <td>
                {{ item.uom or item.stock_uom or "-" }}
            </td>
            <td>{{ item.delivery_date or "-" }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
"""


def build_document(
    title,
    subject,
    body,
    include_items=True,
):
    item_section = ITEM_TABLE if include_items else ""

    return (
        BASE_STYLE
        + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            {{
                company_doc.company_name
                or sales_order.company
                or "Parasramka Engineering Private Limited"
            }}
        </div>

        <div class="pepl-title">
            __TITLE__
        </div>
    </div>

    <table class="pepl-meta">
        <tr>
            <td>
                <strong>Sales Order:</strong>
                {{ sales_order.name }}
            </td>

            <td style="text-align: right;">
                <strong>Document Date:</strong>
                {{ today }}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Customer:</strong>
                {{
                    sales_order.customer_name
                    or sales_order.customer
                    or "-"
                }}
            </td>

            <td style="text-align: right;">
                <strong>Revision:</strong>
                {{ revision }}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Customer PO:</strong>
                {{ sales_order.po_no or "-" }}
            </td>

            <td style="text-align: right;">
                <strong>PO Date:</strong>
                {{ sales_order.po_date or "-" }}
            </td>
        </tr>

        <tr>
            <td colspan="2">
                <strong>Tender / NIT Reference:</strong>
                {{ sales_order.custom_nit_number or "-" }}
            </td>
        </tr>
    </table>

    <p>
        To,<br>
        <strong>
            {{
                sales_order.customer_name
                or sales_order.customer
                or "The Concerned Authority"
            }}
        </strong>
    </p>

    <p>
        <strong>Subject: __SUBJECT__</strong>
    </p>

    <p>Dear Sir/Madam,</p>

    __BODY__

    __ITEM_SECTION__

    <div class="pepl-signature">
        <p>
            For Parasramka Engineering Private Limited
        </p>

        <p style="margin-top: 38px;">
            Authorised Signatory
        </p>
    </div>

    <div class="pepl-note">
        Controlled application template. Final commercial wording,
        formatting, signature and customer-specific requirements
        remain subject to PEPL/client approval.
    </div>
</div>
"""
        .replace("__TITLE__", title)
        .replace("__SUBJECT__", subject)
        .replace("__BODY__", body)
        .replace("__ITEM_SECTION__", item_section)
    )


def build_dispatch_label():
    return (
        BASE_STYLE
        + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            {{
                company_doc.company_name
                or sales_order.company
                or "Parasramka Engineering Private Limited"
            }}
        </div>

        <div class="pepl-title">
            Dispatch / Consignee Label
        </div>
    </div>

    {% for item in sales_order.items or [] %}
    <div class="pepl-label">
        <table style="
            width: 100%;
            border-collapse: collapse;
        ">
            <tr>
                <td colspan="2">
                    <strong>CONSIGNEE</strong><br>
                    {{
                        sales_order.customer_name
                        or sales_order.customer
                        or "-"
                    }}
                </td>
            </tr>

            <tr>
                <td style="width: 50%; padding-top: 10px;">
                    <strong>Sales Order:</strong>
                    {{ sales_order.name }}
                </td>

                <td style="padding-top: 10px;">
                    <strong>Customer PO:</strong>
                    {{ sales_order.po_no or "-" }}
                </td>
            </tr>

            <tr>
                <td style="padding-top: 10px;">
                    <strong>Item Code:</strong>
                    {{ item.item_code or "-" }}
                </td>

                <td style="padding-top: 10px;">
                    <strong>Quantity:</strong>
                    {{ item.qty or 0 }}
                    {{ item.uom or item.stock_uom or "" }}
                </td>
            </tr>

            <tr>
                <td colspan="2" style="padding-top: 10px;">
                    <strong>Description:</strong><br>
                    {{
                        item.description
                        or item.item_name
                        or "-"
                    }}
                </td>
            </tr>

            <tr>
                <td style="padding-top: 10px;">
                    <strong>Delivery Date:</strong>
                    {{ item.delivery_date or "-" }}
                </td>

                <td style="padding-top: 10px;">
                    <strong>Package:</strong>
                    {{ loop.index }}
                </td>
            </tr>
        </table>
    </div>
    {% endfor %}

    <div class="pepl-note">
        Controlled dispatch-label format. Final consignee address,
        package numbering, dimensions, weight, barcode and customer
        markings remain subject to the dispatch process and client
        instructions.
    </div>
</div>
"""
    )


TEMPLATES = {
    "TPL_DRAWING_SPEC_REQUEST": {
        "filename": (
            "DRAWING_SPEC_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Drawing and Specification Request",
            (
                "Request for Approved Drawings, Specifications "
                "and Technical Documents"
            ),
            """
    <p>
        With reference to the above Sales Order, kindly provide the
        latest approved drawings, specifications, inspection
        requirements and related technical documents applicable to
        the following ordered items.
    </p>

    <p>
        The requested information will be used for production,
        quality planning and contractual compliance.
    </p>
""",
        ),
    },

    "TPL_PROOF_SCHEDULE_REQUEST": {
        "filename": (
            "PROOF_SCHEDULE_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Proof Schedule Request",
            "Request for Proof / Inspection Schedule",
            """
    <p>
        Kindly communicate the applicable proof, inspection or test
        schedule for the following ordered items, including the
        inspection authority, location, notice period and witnessing
        requirements.
    </p>
""",
        ),
    },

    "TPL_RAW_MATERIAL_OFFER": {
        "filename": (
            "RAW_MATERIAL_OFFER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Raw Material Inspection Offer",
            "Offer of Raw Material for Inspection",
            """
    <p>
        We hereby offer the raw material procured for the following
        ordered items for inspection, verification or document
        review, as applicable under the contractual quality plan.
    </p>
""",
        ),
    },

    "TPL_QUALITY_SELF_CERTIFICATE": {
        "filename": (
            "QUALITY_SELF_CERTIFICATE_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Quality Self-Certificate",
            "Quality Self-Certification for Supplied Material",
            """
    <p>
        We certify that the following material has been manufactured,
        inspected and verified against the applicable Sales Order,
        approved drawings, specifications and internal quality
        controls.
    </p>

    <p>
        Supporting test and inspection records shall remain
        traceable in the applicable quality records.
    </p>
""",
        ),
    },

    "TPL_NABL_TEST_OFFER": {
        "filename": (
            "NABL_TEST_OFFER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "NABL Laboratory Test Offer",
            "Offer of Material for Testing at NABL Laboratory",
            """
    <p>
        We offer samples relating to the following ordered items for
        testing at an approved NABL-accredited laboratory as required
        under the applicable specification or quality plan.
    </p>
""",
        ),
    },

    "TPL_LOT_NUMBER_REQUEST": {
        "filename": (
            "LOT_NUMBER_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Lot Number and Lot Size Request",
            "Request for Allotment of Lot Number and Lot Size",
            """
    <p>
        Kindly allot or confirm the applicable lot number, lot size
        and inspection grouping for the following ordered items so
        that production and inspection records can be maintained
        accordingly.
    </p>
""",
        ),
    },

    "TPL_BULK_LOT_OFFER": {
        "filename": (
            "BULK_LOT_OFFER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Bulk Lot Inspection Offer",
            "Offer of Bulk Lot for Inspection",
            """
    <p>
        We hereby offer the following bulk lot for inspection in
        accordance with the applicable Sales Order, specifications,
        approved drawings and quality assurance requirements.
    </p>
""",
        ),
    },

    "TPL_WORK_TEST_CERTIFICATE": {
        "filename": (
            "WORK_TEST_CERTIFICATE_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Works Test Certificate",
            "Works Test Certificate",
            """
    <p>
        We certify that the following ordered items have undergone
        the applicable works inspection and tests and have been found
        conforming to the requirements recorded in the available
        manufacturing and quality documents.
    </p>
""",
        ),
    },

    "TPL_DISPATCH_LABEL": {
        "filename": (
            "DISPATCH_LABEL_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_dispatch_label(),
    },
}


def execute():
    for template_name, values in TEMPLATES.items():
        if not frappe.db.exists(
            "PEPL Standard Document Template",
            template_name,
        ):
            frappe.throw(
                "Standard Document Template {0} is missing."
                .format(template_name)
            )

        template = frappe.get_doc(
            "PEPL Standard Document Template",
            template_name,
        )

        template.template_engine = "HTML Print"
        template.output_format = "PDF"
        template.template_version = "1.0"
        template.html_template = values["html"]
        template.required_source_fields = json.dumps(
            COMMON_REQUIRED_FIELDS
        )
        template.output_filename_pattern = values[
            "filename"
        ]
        template.active = 1
        template.status = "Draft"
        template.requires_manual_review = 1

        template.notes = (
            "Controlled Sales Order document template configured "
            "through an application patch. Status remains Draft "
            "pending PEPL/client wording and layout approval."
        )

        template.save(
            ignore_permissions=True
        )

    frappe.clear_cache(
        doctype="PEPL Standard Document Template"
    )
PYcd ~/Desktop/pepl_sales

cat > \
pepl_sales/patches/v1_0/configure_sales_order_standard_document_templates.py \
<<'PY'
import json

import frappe


BASE_STYLE = """
<style>
    body {
        font-family: Arial, sans-serif;
        font-size: 11px;
        line-height: 1.5;
        color: #111;
    }

    .pepl-document {
        padding: 18px 26px;
    }

    .pepl-header {
        text-align: center;
        border-bottom: 1px solid #555;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }

    .pepl-company {
        font-size: 17px;
        font-weight: 700;
    }

    .pepl-title {
        margin-top: 5px;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
    }

    .pepl-meta,
    .pepl-items {
        width: 100%;
        border-collapse: collapse;
    }

    .pepl-meta {
        margin-bottom: 18px;
    }

    .pepl-meta td {
        padding: 3px 0;
        vertical-align: top;
    }

    .pepl-items {
        margin: 16px 0;
    }

    .pepl-items th,
    .pepl-items td {
        border: 1px solid #777;
        padding: 6px;
        vertical-align: top;
    }

    .pepl-items th {
        background: #f2f2f2;
        text-align: left;
    }

    .pepl-signature {
        margin-top: 42px;
    }

    .pepl-note {
        margin-top: 20px;
        padding: 8px;
        border: 1px solid #999;
        font-size: 9px;
        color: #555;
    }

    .pepl-label {
        border: 2px solid #222;
        padding: 14px;
        margin-bottom: 12px;
        page-break-inside: avoid;
    }
</style>
"""


COMMON_REQUIRED_FIELDS = [
    "source_doctype",
    "source_document",
    "customer",
    "sales_order.name",
    "sales_order.customer",
    "sales_order.transaction_date",
    "sales_order.company",
    "sales_order.items",
]


ITEM_TABLE = """
<table class="pepl-items">
    <thead>
        <tr>
            <th style="width: 6%;">Sl.</th>
            <th style="width: 18%;">Item Code</th>
            <th>Description</th>
            <th style="width: 12%;">Quantity</th>
            <th style="width: 10%;">UOM</th>
            <th style="width: 14%;">Delivery Date</th>
        </tr>
    </thead>
    <tbody>
        {% for item in sales_order.items or [] %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ item.item_code or "-" }}</td>
            <td>
                {{
                    item.description
                    or item.item_name
                    or "-"
                }}
            </td>
            <td>{{ item.qty or 0 }}</td>
            <td>
                {{ item.uom or item.stock_uom or "-" }}
            </td>
            <td>{{ item.delivery_date or "-" }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
"""


def build_document(
    title,
    subject,
    body,
    include_items=True,
):
    item_section = ITEM_TABLE if include_items else ""

    return (
        BASE_STYLE
        + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            {{
                company_doc.company_name
                or sales_order.company
                or "Parasramka Engineering Private Limited"
            }}
        </div>

        <div class="pepl-title">
            __TITLE__
        </div>
    </div>

    <table class="pepl-meta">
        <tr>
            <td>
                <strong>Sales Order:</strong>
                {{ sales_order.name }}
            </td>

            <td style="text-align: right;">
                <strong>Document Date:</strong>
                {{ today }}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Customer:</strong>
                {{
                    sales_order.customer_name
                    or sales_order.customer
                    or "-"
                }}
            </td>

            <td style="text-align: right;">
                <strong>Revision:</strong>
                {{ revision }}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Customer PO:</strong>
                {{ sales_order.po_no or "-" }}
            </td>

            <td style="text-align: right;">
                <strong>PO Date:</strong>
                {{ sales_order.po_date or "-" }}
            </td>
        </tr>

        <tr>
            <td colspan="2">
                <strong>Tender / NIT Reference:</strong>
                {{ sales_order.custom_nit_number or "-" }}
            </td>
        </tr>
    </table>

    <p>
        To,<br>
        <strong>
            {{
                sales_order.customer_name
                or sales_order.customer
                or "The Concerned Authority"
            }}
        </strong>
    </p>

    <p>
        <strong>Subject: __SUBJECT__</strong>
    </p>

    <p>Dear Sir/Madam,</p>

    __BODY__

    __ITEM_SECTION__

    <div class="pepl-signature">
        <p>
            For Parasramka Engineering Private Limited
        </p>

        <p style="margin-top: 38px;">
            Authorised Signatory
        </p>
    </div>

    <div class="pepl-note">
        Controlled application template. Final commercial wording,
        formatting, signature and customer-specific requirements
        remain subject to PEPL/client approval.
    </div>
</div>
"""
        .replace("__TITLE__", title)
        .replace("__SUBJECT__", subject)
        .replace("__BODY__", body)
        .replace("__ITEM_SECTION__", item_section)
    )


def build_dispatch_label():
    return (
        BASE_STYLE
        + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            {{
                company_doc.company_name
                or sales_order.company
                or "Parasramka Engineering Private Limited"
            }}
        </div>

        <div class="pepl-title">
            Dispatch / Consignee Label
        </div>
    </div>

    {% for item in sales_order.items or [] %}
    <div class="pepl-label">
        <table style="
            width: 100%;
            border-collapse: collapse;
        ">
            <tr>
                <td colspan="2">
                    <strong>CONSIGNEE</strong><br>
                    {{
                        sales_order.customer_name
                        or sales_order.customer
                        or "-"
                    }}
                </td>
            </tr>

            <tr>
                <td style="width: 50%; padding-top: 10px;">
                    <strong>Sales Order:</strong>
                    {{ sales_order.name }}
                </td>

                <td style="padding-top: 10px;">
                    <strong>Customer PO:</strong>
                    {{ sales_order.po_no or "-" }}
                </td>
            </tr>

            <tr>
                <td style="padding-top: 10px;">
                    <strong>Item Code:</strong>
                    {{ item.item_code or "-" }}
                </td>

                <td style="padding-top: 10px;">
                    <strong>Quantity:</strong>
                    {{ item.qty or 0 }}
                    {{ item.uom or item.stock_uom or "" }}
                </td>
            </tr>

            <tr>
                <td colspan="2" style="padding-top: 10px;">
                    <strong>Description:</strong><br>
                    {{
                        item.description
                        or item.item_name
                        or "-"
                    }}
                </td>
            </tr>

            <tr>
                <td style="padding-top: 10px;">
                    <strong>Delivery Date:</strong>
                    {{ item.delivery_date or "-" }}
                </td>

                <td style="padding-top: 10px;">
                    <strong>Package:</strong>
                    {{ loop.index }}
                </td>
            </tr>
        </table>
    </div>
    {% endfor %}

    <div class="pepl-note">
        Controlled dispatch-label format. Final consignee address,
        package numbering, dimensions, weight, barcode and customer
        markings remain subject to the dispatch process and client
        instructions.
    </div>
</div>
"""
    )


TEMPLATES = {
    "TPL_DRAWING_SPEC_REQUEST": {
        "filename": (
            "DRAWING_SPEC_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Drawing and Specification Request",
            (
                "Request for Approved Drawings, Specifications "
                "and Technical Documents"
            ),
            """
    <p>
        With reference to the above Sales Order, kindly provide the
        latest approved drawings, specifications, inspection
        requirements and related technical documents applicable to
        the following ordered items.
    </p>

    <p>
        The requested information will be used for production,
        quality planning and contractual compliance.
    </p>
""",
        ),
    },

    "TPL_PROOF_SCHEDULE_REQUEST": {
        "filename": (
            "PROOF_SCHEDULE_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Proof Schedule Request",
            "Request for Proof / Inspection Schedule",
            """
    <p>
        Kindly communicate the applicable proof, inspection or test
        schedule for the following ordered items, including the
        inspection authority, location, notice period and witnessing
        requirements.
    </p>
""",
        ),
    },

    "TPL_RAW_MATERIAL_OFFER": {
        "filename": (
            "RAW_MATERIAL_OFFER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Raw Material Inspection Offer",
            "Offer of Raw Material for Inspection",
            """
    <p>
        We hereby offer the raw material procured for the following
        ordered items for inspection, verification or document
        review, as applicable under the contractual quality plan.
    </p>
""",
        ),
    },

    "TPL_QUALITY_SELF_CERTIFICATE": {
        "filename": (
            "QUALITY_SELF_CERTIFICATE_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Quality Self-Certificate",
            "Quality Self-Certification for Supplied Material",
            """
    <p>
        We certify that the following material has been manufactured,
        inspected and verified against the applicable Sales Order,
        approved drawings, specifications and internal quality
        controls.
    </p>

    <p>
        Supporting test and inspection records shall remain
        traceable in the applicable quality records.
    </p>
""",
        ),
    },

    "TPL_NABL_TEST_OFFER": {
        "filename": (
            "NABL_TEST_OFFER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "NABL Laboratory Test Offer",
            "Offer of Material for Testing at NABL Laboratory",
            """
    <p>
        We offer samples relating to the following ordered items for
        testing at an approved NABL-accredited laboratory as required
        under the applicable specification or quality plan.
    </p>
""",
        ),
    },

    "TPL_LOT_NUMBER_REQUEST": {
        "filename": (
            "LOT_NUMBER_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Lot Number and Lot Size Request",
            "Request for Allotment of Lot Number and Lot Size",
            """
    <p>
        Kindly allot or confirm the applicable lot number, lot size
        and inspection grouping for the following ordered items so
        that production and inspection records can be maintained
        accordingly.
    </p>
""",
        ),
    },

    "TPL_BULK_LOT_OFFER": {
        "filename": (
            "BULK_LOT_OFFER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Bulk Lot Inspection Offer",
            "Offer of Bulk Lot for Inspection",
            """
    <p>
        We hereby offer the following bulk lot for inspection in
        accordance with the applicable Sales Order, specifications,
        approved drawings and quality assurance requirements.
    </p>
""",
        ),
    },

    "TPL_WORK_TEST_CERTIFICATE": {
        "filename": (
            "WORK_TEST_CERTIFICATE_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_document(
            "Works Test Certificate",
            "Works Test Certificate",
            """
    <p>
        We certify that the following ordered items have undergone
        the applicable works inspection and tests and have been found
        conforming to the requirements recorded in the available
        manufacturing and quality documents.
    </p>
""",
        ),
    },

    "TPL_DISPATCH_LABEL": {
        "filename": (
            "DISPATCH_LABEL_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "html": build_dispatch_label(),
    },
}


def execute():
    for template_name, values in TEMPLATES.items():
        if not frappe.db.exists(
            "PEPL Standard Document Template",
            template_name,
        ):
            frappe.throw(
                "Standard Document Template {0} is missing."
                .format(template_name)
            )

        template = frappe.get_doc(
            "PEPL Standard Document Template",
            template_name,
        )

        template.template_engine = "HTML Print"
        template.output_format = "PDF"
        template.template_version = "1.0"
        template.html_template = values["html"]
        template.required_source_fields = json.dumps(
            COMMON_REQUIRED_FIELDS
        )
        template.output_filename_pattern = values[
            "filename"
        ]
        template.active = 1
        template.status = "Draft"
        template.requires_manual_review = 1

        template.notes = (
            "Controlled Sales Order document template configured "
            "through an application patch. Status remains Draft "
            "pending PEPL/client wording and layout approval."
        )

        template.save(
            ignore_permissions=True
        )

    frappe.clear_cache(
        doctype="PEPL Standard Document Template"
    )
