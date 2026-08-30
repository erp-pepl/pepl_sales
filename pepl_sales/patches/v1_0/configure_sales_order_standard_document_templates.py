import json

import frappe


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


TEMPLATE_CONFIG = {
    "TPL_DRAWING_SPEC_REQUEST": {
        "title": "Drawing and Specification Request",
        "subject": (
            "Request for Approved Drawings, Specifications "
            "and Technical Documents"
        ),
        "body": (
            "Kindly provide the latest approved drawings, "
            "specifications, inspection requirements and related "
            "technical documents applicable to the ordered items."
        ),
        "filename": (
            "DRAWING_SPEC_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
    },
    "TPL_PROOF_SCHEDULE_REQUEST": {
        "title": "Proof Schedule Request",
        "subject": "Request for Proof / Inspection Schedule",
        "body": (
            "Kindly communicate the applicable proof, inspection "
            "or test schedule, including inspection authority, "
            "location, notice period and witnessing requirements."
        ),
        "filename": (
            "PROOF_SCHEDULE_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
    },
    "TPL_RAW_MATERIAL_OFFER": {
        "title": "Raw Material Inspection Offer",
        "subject": "Offer of Raw Material for Inspection",
        "body": (
            "We hereby offer the raw material procured for the "
            "ordered items for inspection, verification or "
            "document review under the contractual quality plan."
        ),
        "filename": (
            "RAW_MATERIAL_OFFER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
    },
    "TPL_QUALITY_SELF_CERTIFICATE": {
        "title": "Quality Self-Certificate",
        "subject": (
            "Quality Self-Certification for Supplied Material"
        ),
        "body": (
            "We certify that the ordered material has been "
            "manufactured, inspected and verified against the "
            "applicable order, drawings, specifications and "
            "internal quality controls."
        ),
        "filename": (
            "QUALITY_SELF_CERTIFICATE_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
    },
    "TPL_NABL_TEST_OFFER": {
        "title": "NABL Laboratory Test Offer",
        "subject": (
            "Offer of Material for Testing at NABL Laboratory"
        ),
        "body": (
            "We offer samples relating to the ordered items for "
            "testing at an approved NABL-accredited laboratory, "
            "as required by the applicable specification."
        ),
        "filename": (
            "NABL_TEST_OFFER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
    },
    "TPL_LOT_NUMBER_REQUEST": {
        "title": "Lot Number and Lot Size Request",
        "subject": (
            "Request for Allotment of Lot Number and Lot Size"
        ),
        "body": (
            "Kindly allot or confirm the applicable lot number, "
            "lot size and inspection grouping for the ordered "
            "items."
        ),
        "filename": (
            "LOT_NUMBER_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
    },
    "TPL_BULK_LOT_OFFER": {
        "title": "Bulk Lot Inspection Offer",
        "subject": "Offer of Bulk Lot for Inspection",
        "body": (
            "We hereby offer the following bulk lot for inspection "
            "in accordance with the applicable Sales Order, "
            "specifications, drawings and quality requirements."
        ),
        "filename": (
            "BULK_LOT_OFFER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
    },
    "TPL_WORK_TEST_CERTIFICATE": {
        "title": "Works Test Certificate",
        "subject": "Works Test Certificate",
        "body": (
            "We certify that the ordered items have undergone the "
            "applicable works inspections and tests and have been "
            "found conforming to the available manufacturing and "
            "quality requirements."
        ),
        "filename": (
            "WORK_TEST_CERTIFICATE_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
    },
    "TPL_DISPATCH_LABEL": {
        "title": "Dispatch / Consignee Label",
        "subject": "Dispatch Identification",
        "body": (
            "This controlled document identifies the consignee, "
            "Sales Order and item quantities for dispatch."
        ),
        "filename": (
            "DISPATCH_LABEL_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
    },
}


HTML_TEMPLATE = """
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
        font-weight: bold;
    }

    .pepl-title {
        margin-top: 5px;
        font-size: 13px;
        font-weight: bold;
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
        margin-top: 16px;
        margin-bottom: 16px;
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
        border: 1px solid #999;
        padding: 8px;
        font-size: 9px;
        color: #555;
    }
</style>

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
                <strong>Date:</strong>
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

    <p>__BODY__</p>

    <table class="pepl-items">
        <thead>
            <tr>
                <th>Sl.</th>
                <th>Item Code</th>
                <th>Description</th>
                <th>Quantity</th>
                <th>UOM</th>
                <th>Delivery Date</th>
            </tr>
        </thead>

        <tbody>
            {% for item in sales_order['items'] or [] %}
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

    <div class="pepl-signature">
        <p>
            For Parasramka Engineering Private Limited
        </p>

        <p style="margin-top: 38px;">
            Authorised Signatory
        </p>
    </div>

    <div class="pepl-note">
        Controlled application template. Final wording, formatting,
        signature and customer-specific requirements remain subject
        to PEPL/client approval.
    </div>
</div>
"""


def get_html(config):
    html = HTML_TEMPLATE.replace(
        "__TITLE__",
        config["title"],
    )

    html = html.replace(
        "__SUBJECT__",
        config["subject"],
    )

    html = html.replace(
        "__BODY__",
        config["body"],
    )

    return html


def execute():
    for template_name, config in TEMPLATE_CONFIG.items():
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
        template.html_template = get_html(config)

        template.required_source_fields = json.dumps(
            COMMON_REQUIRED_FIELDS
        )

        template.output_filename_pattern = config[
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
