import json

import frappe


REQUIRED_FIELDS = [
    "payment_tracker.name",
    "payment_tracker.linked_sales_invoice",
    "payment_tracker.customer",
    "payment_tracker.invoice_date",
    "payment_tracker.invoice_amount",
    "payment_tracker.total_amount_received",
    "payment_tracker.total_outstanding",
    "payment_tracker.payment_status",
    "sales_invoice.name",
    "sales_invoice.posting_date",
    "sales_invoice.customer",
    "sales_invoice.company",
]


HTML_TEMPLATE = """
<style>
    body {
        font-family: Arial, sans-serif;
        font-size: 11px;
        line-height: 1.55;
        color: #111;
    }

    .pepl-document {
        padding: 18px 28px;
    }

    .pepl-header {
        text-align: center;
        border-bottom: 1px solid #555;
        padding-bottom: 10px;
        margin-bottom: 22px;
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
    .pepl-summary {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 18px;
    }

    .pepl-meta td {
        padding: 3px 0;
        vertical-align: top;
    }

    .pepl-summary th,
    .pepl-summary td {
        border: 1px solid #777;
        padding: 7px;
        text-align: left;
        vertical-align: top;
    }

    .pepl-summary th {
        width: 42%;
        background: #f2f2f2;
    }

    .pepl-signature {
        margin-top: 44px;
    }

    .pepl-note {
        margin-top: 24px;
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
            Payment Request Letter
        </div>
    </div>

    <table class="pepl-meta">
        <tr>
            <td>
                <strong>Reference:</strong>
                {{ payment_tracker.name }}
            </td>

            <td style="text-align: right;">
                <strong>Date:</strong>
                {{ today }}
            </td>
        </tr>

        <tr>
            <td>
                <strong>Sales Invoice:</strong>
                {{ payment_tracker.linked_sales_invoice }}
            </td>

            <td style="text-align: right;">
                <strong>Invoice Date:</strong>
                {{
                    sales_invoice.posting_date
                    or payment_tracker.invoice_date
                }}
            </td>
        </tr>
    </table>

    <p>
        To,<br>
        <strong>
            {{
                sales_invoice.customer_name
                or payment_tracker.customer
                or "The Concerned Authority"
            }}
        </strong>
    </p>

    {% if customer_address %}
    <p>
        {{ customer_address.address_line1 or "" }}<br>
        {% if customer_address.address_line2 %}
            {{ customer_address.address_line2 }}<br>
        {% endif %}
        {{ customer_address.city or "" }}
        {% if customer_address.state %}
            , {{ customer_address.state }}
        {% endif %}
        {% if customer_address.pincode %}
            - {{ customer_address.pincode }}
        {% endif %}
    </p>
    {% endif %}

    <p>
        <strong>
            Subject: Request for release of payment against
            Sales Invoice
            {{ payment_tracker.linked_sales_invoice }}
        </strong>
    </p>

    <p>Dear Sir/Madam,</p>

    <p>
        We request you to kindly arrange release of the outstanding
        payment against the Sales Invoice referenced below.
    </p>

    <table class="pepl-summary">
        <tr>
            <th>Sales Invoice</th>
            <td>
                {{ payment_tracker.linked_sales_invoice }}
            </td>
        </tr>

        <tr>
            <th>Linked Sales Order</th>
            <td>
                {{
                    payment_tracker.linked_sales_order
                    or "-"
                }}
            </td>
        </tr>

        <tr>
            <th>Invoice Amount</th>
            <td>
                INR
                {{
                    payment_tracker.invoice_amount
                    or sales_invoice.grand_total
                    or 0
                }}
            </td>
        </tr>

        <tr>
            <th>Total Amount Received</th>
            <td>
                INR
                {{
                    payment_tracker.total_amount_received
                    or 0
                }}
            </td>
        </tr>

        <tr>
            <th>Outstanding Amount</th>
            <td>
                INR
                {{
                    payment_tracker.total_outstanding
                    or 0
                }}
            </td>
        </tr>

        <tr>
            <th>Payment Status</th>
            <td>
                {{ payment_tracker.payment_status }}
            </td>
        </tr>

        <tr>
            <th>Bill Submission Date</th>
            <td>
                {{
                    payment_tracker.bills_submission_date
                    or "-"
                }}
            </td>
        </tr>

        <tr>
            <th>Bill Reference Number</th>
            <td>
                {{
                    payment_tracker.bill_reference_number
                    or "-"
                }}
            </td>
        </tr>

        {% if payment_tracker.rnote_number %}
        <tr>
            <th>R-Note Number</th>
            <td>
                {{ payment_tracker.rnote_number }}
            </td>
        </tr>
        {% endif %}

        {% if payment_tracker.inote_number %}
        <tr>
            <th>I-Note Number</th>
            <td>
                {{ payment_tracker.inote_number }}
            </td>
        </tr>
        {% endif %}

        {% if payment_tracker.jcc_number %}
        <tr>
            <th>JCC Number</th>
            <td>
                {{ payment_tracker.jcc_number }}
            </td>
        </tr>
        {% endif %}

        {% if payment_tracker.co7_number %}
        <tr>
            <th>CO7 Number</th>
            <td>
                {{ payment_tracker.co7_number }}
            </td>
        </tr>
        {% endif %}
    </table>

    <p>
        We request you to process the outstanding amount at the
        earliest and confirm the expected payment date.
    </p>

    <div class="pepl-signature">
        <p>
            For Parasramka Engineering Private Limited
        </p>

        <p style="margin-top: 38px;">
            Authorised Signatory
        </p>
    </div>

    <div class="pepl-note">
        Controlled application template. Final wording, customer
        address, statutory references and authorised signature remain
        subject to PEPL/client approval.
    </div>
</div>
"""


def execute():
    template_name = "TPL_PAYMENT_REQUEST"

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

    if (
        template.document_requirement
        != "PAYMENT_REQUEST"
    ):
        frappe.throw(
            "Template {0} is not linked to "
            "PAYMENT_REQUEST."
            .format(template.name)
        )

    requirement = frappe.get_doc(
        "PEPL Document Requirement",
        template.document_requirement,
    )

    if (
        requirement.source_transaction
        != "Payment Tracker"
    ):
        frappe.throw(
            "PAYMENT_REQUEST must use Payment Tracker "
            "as its source transaction."
        )

    template.template_engine = "HTML Print"
    template.output_format = "PDF"
    template.template_version = "1.0"
    template.html_template = HTML_TEMPLATE
    template.required_source_fields = (
        json.dumps(
            REQUIRED_FIELDS
        )
    )

    template.output_filename_pattern = (
        "PAYMENT_REQUEST_"
        "{{ source_document }}_"
        "R{{ revision }}.pdf"
    )

    template.active = 1
    template.status = "Draft"
    template.requires_manual_review = 1

    template.notes = (
        "Controlled Payment Request Letter configured "
        "through an application patch. Status remains "
        "Draft pending PEPL/client wording and layout "
        "approval."
    )

    template.save(
        ignore_permissions=True
    )

    frappe.clear_cache(
        doctype="PEPL Standard Document Template"
    )
