import json

import frappe


COMMON_REQUIRED_FIELDS = [
    "source_doctype",
    "source_document",
    "customer",
    "sales_invoice.name",
    "sales_invoice.customer",
    "sales_invoice.posting_date",
    "sales_invoice.company",
    "sales_invoice.currency",
    "sales_invoice.grand_total",
    "sales_invoice.items",
]


TEMPLATE_CONFIG = {
    "TPL_GST_SUMMARY": {
        "title": "GST Summary",
        "subject": "GST Summary for Sales Invoice",
        "filename": (
            "GST_SUMMARY_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "body": """
<p>
    This document presents the GST and invoice-value summary for the
    referenced Sales Invoice.
</p>

<table class="pepl-summary">
    <tr>
        <th>Net Total</th>
        <td>
            {{ sales_invoice.currency }}
            {{ sales_invoice.net_total or 0 }}
        </td>
    </tr>

    <tr>
        <th>Total Taxes and Charges</th>
        <td>
            {{ sales_invoice.currency }}
            {{
                sales_invoice.total_taxes_and_charges
                or 0
            }}
        </td>
    </tr>

    <tr>
        <th>Grand Total</th>
        <td>
            {{ sales_invoice.currency }}
            {{ sales_invoice.grand_total or 0 }}
        </td>
    </tr>

    <tr>
        <th>Rounded Total</th>
        <td>
            {{ sales_invoice.currency }}
            {{
                sales_invoice.rounded_total
                or sales_invoice.grand_total
                or 0
            }}
        </td>
    </tr>
</table>

{% if sales_invoice.taxes %}
<h4>Tax Details</h4>

<table class="pepl-items">
    <thead>
        <tr>
            <th>Tax Type</th>
            <th>Account</th>
            <th>Rate</th>
            <th>Tax Amount</th>
        </tr>
    </thead>

    <tbody>
        {% for tax in sales_invoice.taxes %}
        <tr>
            <td>{{ tax.charge_type or "-" }}</td>
            <td>{{ tax.account_head or "-" }}</td>
            <td>{{ tax.rate or 0 }}%</td>
            <td>
                {{ sales_invoice.currency }}
                {{ tax.tax_amount or 0 }}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endif %}
""",
    },
    "TPL_GUARANTEE_CERTIFICATE": {
        "title": "After-Invoice Guarantee Certificate",
        "subject": (
            "Guarantee Certificate against Sales Invoice "
            "{{ sales_invoice.name }}"
        ),
        "filename": (
            "GUARANTEE_CERTIFICATE_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "body": """
<p>
    We certify that the material supplied under the referenced Sales
    Invoice is covered by the contractual guarantee or warranty
    obligations applicable to the corresponding order and approved
    technical requirements.
</p>

<p>
    The guarantee period, exclusions and remedies shall remain
    governed by the applicable purchase order, contract, approved
    specifications and commercial terms.
</p>
""",
    },
    "TPL_CONTRACTOR_BILL": {
        "title": "Contractor's Bill",
        "subject": (
            "Contractor's Bill against Sales Invoice "
            "{{ sales_invoice.name }}"
        ),
        "filename": (
            "CONTRACTOR_BILL_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "body": """
<p>
    This controlled bill summary is submitted against the referenced
    Sales Invoice and the associated supply or contractual work.
</p>

<table class="pepl-summary">
    <tr>
        <th>Invoice Number</th>
        <td>{{ sales_invoice.name }}</td>
    </tr>

    <tr>
        <th>Invoice Date</th>
        <td>{{ sales_invoice.posting_date }}</td>
    </tr>

    <tr>
        <th>Customer</th>
        <td>
            {{
                sales_invoice.customer_name
                or sales_invoice.customer
                or "-"
            }}
        </td>
    </tr>

    <tr>
        <th>Invoice Amount</th>
        <td>
            {{ sales_invoice.currency }}
            {{ sales_invoice.grand_total or 0 }}
        </td>
    </tr>

    <tr>
        <th>Linked Sales Orders</th>
        <td>
            {{
                linked_sales_orders
                | join(", ")
                if linked_sales_orders
                else "-"
            }}
        </td>
    </tr>
</table>
""",
    },
}


BASE_HTML = """
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
    .pepl-items,
    .pepl-summary {
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

    .pepl-items,
    .pepl-summary {
        margin-top: 14px;
        margin-bottom: 16px;
    }

    .pepl-items th,
    .pepl-items td,
    .pepl-summary th,
    .pepl-summary td {
        border: 1px solid #777;
        padding: 6px;
        vertical-align: top;
    }

    .pepl-items th,
    .pepl-summary th {
        background: #f2f2f2;
        text-align: left;
    }

    .pepl-summary th {
        width: 42%;
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
                or sales_invoice.company
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
                <strong>Sales Invoice:</strong>
                {{ sales_invoice.name }}
            </td>

            <td style="text-align: right;">
                <strong>Invoice Date:</strong>
                {{ sales_invoice.posting_date }}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Customer:</strong>
                {{
                    sales_invoice.customer_name
                    or sales_invoice.customer
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
                {{ sales_invoice.po_no or "-" }}
            </td>

            <td style="text-align: right;">
                <strong>Currency:</strong>
                {{ sales_invoice.currency or "-" }}
            </td>
        </tr>
    </table>

    <p>
        To,<br>
        <strong>
            {{
                sales_invoice.customer_name
                or sales_invoice.customer
                or "The Concerned Authority"
            }}
        </strong>
    </p>

    <p>
        <strong>Subject: __SUBJECT__</strong>
    </p>

    <p>Dear Sir/Madam,</p>

    __BODY__

    <h4>Invoice Items</h4>

    <table class="pepl-items">
        <thead>
            <tr>
                <th>Sl.</th>
                <th>Item Code</th>
                <th>Description</th>
                <th>Quantity</th>
                <th>Rate</th>
                <th>Amount</th>
            </tr>
        </thead>

        <tbody>
            {% for item in sales_invoice.items or [] %}
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
                <td>
                    {{ item.qty or 0 }}
                    {{ item.uom or "" }}
                </td>
                <td>
                    {{ sales_invoice.currency }}
                    {{ item.rate or 0 }}
                </td>
                <td>
                    {{ sales_invoice.currency }}
                    {{ item.amount or 0 }}
                </td>
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
        Controlled application template. Final wording, statutory
        content, signature and customer-specific format remain
        subject to PEPL/client approval.
    </div>
</div>
"""


def get_html(config):
    html = BASE_HTML.replace(
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

        template.required_source_fields = (
            json.dumps(
                COMMON_REQUIRED_FIELDS
            )
        )

        template.output_filename_pattern = config[
            "filename"
        ]

        template.active = 1
        template.status = "Draft"
        template.requires_manual_review = 1

        template.notes = (
            "Controlled Sales Invoice document template "
            "configured through an application patch. "
            "Status remains Draft pending PEPL/client "
            "statutory wording and layout approval."
        )

        template.save(
            ignore_permissions=True
        )

    frappe.clear_cache(
        doctype="PEPL Standard Document Template"
    )
