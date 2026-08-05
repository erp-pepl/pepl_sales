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
        margin-bottom: 22px;
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

    .pepl-meta {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }

    .pepl-meta td {
        padding: 3px 0;
        vertical-align: top;
    }

    .pepl-table {
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
    }

    .pepl-table th,
    .pepl-table td {
        border: 1px solid #777;
        padding: 6px 8px;
        vertical-align: top;
    }

    .pepl-table th {
        width: 34%;
        text-align: left;
        background: #f2f2f2;
    }

    .pepl-signature {
        margin-top: 44px;
    }

    .pepl-note {
        margin-top: 22px;
        font-size: 9px;
        color: #555;
    }
</style>
"""


COMMON_REQUIRED_FIELDS = [
    "source_doctype",
    "source_document",
    "customer",
    "sales_order.name",
    "selected_psd_entry.name",
    "selected_psd_entry.security_mode",
    "selected_psd_entry.bg_number",
    "selected_psd_entry.bg_date",
    "selected_psd_entry.bg_amount",
    "selected_psd_entry.bg_expiry_date",
    "selected_psd_entry.claim_expiry_date",
    "selected_psd_entry.issuing_bank",
    "selected_psd_entry.issuing_bank_branch",
    "selected_psd_entry.beneficiary_name",
    "selected_psd_entry.beneficiary_address",
]


TEMPLATES = {
    "TPL_PSD_BG_SUBMISSION_COVER": {
        "status": "Approved",
        "filename": (
            "PSD_BG_SUBMISSION_COVER_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "required_fields": (
            COMMON_REQUIRED_FIELDS
            + [
                "selected_psd_entry.bg_submission_reference",
                "selected_psd_entry.bg_submission_date",
            ]
        ),
        "html": BASE_STYLE + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            PARASRAMKA ENGINEERING PRIVATE LIMITED
        </div>
        <div class="pepl-title">
            Bank Guarantee Submission Covering Letter
        </div>
    </div>

    <table class="pepl-meta">
        <tr>
            <td>
                <strong>Reference:</strong>
                {{ selected_psd_entry.bg_submission_reference
                    or source_document }}
            </td>
            <td style="text-align: right;">
                <strong>Date:</strong>
                {{ selected_psd_entry.bg_submission_date
                    or today }}
            </td>
        </tr>
    </table>

    <p>
        To,<br>
        <strong>
            {{ selected_psd_entry.beneficiary_name
                or customer
                or "The Concerned Authority" }}
        </strong><br>
        {{ selected_psd_entry.beneficiary_address or "" }}
    </p>

    <p>
        <strong>
            Subject: Submission of Bank Guarantee
        </strong>
    </p>

    <p>
        Dear Sir/Madam,
    </p>

    <p>
        With reference to Sales Order
        <strong>{{ sales_order.name or "-" }}</strong>,
        we are submitting the Bank Guarantee detailed below
        for your records and necessary action.
    </p>

    <table class="pepl-table">
        <tr>
            <th>Bank Guarantee Number</th>
            <td>{{ selected_psd_entry.bg_number or "-" }}</td>
        </tr>
        <tr>
            <th>Bank Guarantee Date</th>
            <td>{{ selected_psd_entry.bg_date or "-" }}</td>
        </tr>
        <tr>
            <th>Bank Guarantee Amount</th>
            <td>{{ selected_psd_entry.bg_amount or "-" }}</td>
        </tr>
        <tr>
            <th>Expiry Date</th>
            <td>
                {{ selected_psd_entry.bg_expiry_date or "-" }}
            </td>
        </tr>
        <tr>
            <th>Claim Expiry Date</th>
            <td>
                {{ selected_psd_entry.claim_expiry_date or "-" }}
            </td>
        </tr>
        <tr>
            <th>Issuing Bank</th>
            <td>
                {{ selected_psd_entry.issuing_bank or "-" }}
                {% if selected_psd_entry.issuing_bank_branch %}
                    — {{ selected_psd_entry.issuing_bank_branch }}
                {% endif %}
            </td>
        </tr>
    </table>

    <p>
        Kindly acknowledge receipt of the above document.
    </p>

    <div class="pepl-signature">
        <p>
            For Parasramka Engineering Private Limited
        </p>
        <p style="margin-top: 38px;">
            Authorised Signatory
        </p>
    </div>
</div>
""",
    },

    "TPL_PSD_BG_COLLECTION_AUTHORITY": {
        "status": "Draft",
        "filename": (
            "PSD_BG_COLLECTION_AUTHORITY_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "required_fields": (
            COMMON_REQUIRED_FIELDS
            + [
                "selected_psd_entry.bg_application_reference",
            ]
        ),
        "html": BASE_STYLE + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            PARASRAMKA ENGINEERING PRIVATE LIMITED
        </div>
        <div class="pepl-title">
            Authority Letter for Collection of Bank Guarantee
        </div>
    </div>

    <table class="pepl-meta">
        <tr>
            <td>
                <strong>Reference:</strong>
                {{ selected_psd_entry.bg_application_reference
                    or source_document }}
            </td>
            <td style="text-align: right;">
                <strong>Date:</strong> {{ today }}
            </td>
        </tr>
    </table>

    <p>
        To,<br>
        <strong>
            {{ selected_psd_entry.issuing_bank
                or "The Branch Manager" }}
        </strong><br>
        {{ selected_psd_entry.issuing_bank_branch or "" }}
    </p>

    <p>
        <strong>
            Subject: Authority to Collect Bank Guarantee
        </strong>
    </p>

    <p>
        Dear Sir/Madam,
    </p>

    <p>
        We hereby authorise the bearer of this letter, whose
        identification shall be verified by your branch, to collect
        the Bank Guarantee prepared against our application and
        relating to Sales Order
        <strong>{{ sales_order.name or "-" }}</strong>.
    </p>

    <table class="pepl-table">
        <tr>
            <th>Bank Guarantee Number</th>
            <td>{{ selected_psd_entry.bg_number or "-" }}</td>
        </tr>
        <tr>
            <th>Beneficiary</th>
            <td>
                {{ selected_psd_entry.beneficiary_name or "-" }}
            </td>
        </tr>
        <tr>
            <th>Amount</th>
            <td>{{ selected_psd_entry.bg_amount or "-" }}</td>
        </tr>
    </table>

    <p>
        Kindly release the document after completing the applicable
        identification and acknowledgement formalities.
    </p>

    <div class="pepl-signature">
        <p>
            For Parasramka Engineering Private Limited
        </p>
        <p style="margin-top: 38px;">
            Authorised Signatory
        </p>
    </div>
</div>
""",
    },

    "TPL_PSD_BG_DEBIT_AUTHORITY": {
        "status": "Draft",
        "filename": (
            "PSD_BG_DEBIT_AUTHORITY_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "required_fields": (
            COMMON_REQUIRED_FIELDS
            + [
                "selected_psd_entry.bg_application_reference",
            ]
        ),
        "html": BASE_STYLE + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            PARASRAMKA ENGINEERING PRIVATE LIMITED
        </div>
        <div class="pepl-title">
            Bank Guarantee Request-cum-Debit Authority
        </div>
    </div>

    <table class="pepl-meta">
        <tr>
            <td>
                <strong>Reference:</strong>
                {{ selected_psd_entry.bg_application_reference
                    or source_document }}
            </td>
            <td style="text-align: right;">
                <strong>Date:</strong> {{ today }}
            </td>
        </tr>
    </table>

    <p>
        To,<br>
        <strong>
            {{ selected_psd_entry.issuing_bank
                or "The Branch Manager" }}
        </strong><br>
        {{ selected_psd_entry.issuing_bank_branch or "" }}
    </p>

    <p>
        <strong>
            Subject: Request for Issuance of Bank Guarantee and
            Authority to Debit Applicable Charges
        </strong>
    </p>

    <p>
        Dear Sir/Madam,
    </p>

    <p>
        Please arrange to issue a Bank Guarantee with the following
        particulars and debit the applicable margin, commission,
        taxes and bank charges to our designated account maintained
        with your branch.
    </p>

    <table class="pepl-table">
        <tr>
            <th>Beneficiary</th>
            <td>
                {{ selected_psd_entry.beneficiary_name or "-" }}
            </td>
        </tr>
        <tr>
            <th>Beneficiary Address</th>
            <td>
                {{ selected_psd_entry.beneficiary_address or "-" }}
            </td>
        </tr>
        <tr>
            <th>Sales Order</th>
            <td>{{ sales_order.name or "-" }}</td>
        </tr>
        <tr>
            <th>Guarantee Amount</th>
            <td>{{ selected_psd_entry.bg_amount or "-" }}</td>
        </tr>
        <tr>
            <th>Expiry Date</th>
            <td>
                {{ selected_psd_entry.bg_expiry_date or "-" }}
            </td>
        </tr>
        <tr>
            <th>Claim Expiry Date</th>
            <td>
                {{ selected_psd_entry.claim_expiry_date or "-" }}
            </td>
        </tr>
    </table>

    <p>
        The final guarantee text and all bank-specific formalities
        shall be governed by the documents accepted by the bank and
        beneficiary.
    </p>

    <div class="pepl-signature">
        <p>
            For Parasramka Engineering Private Limited
        </p>
        <p style="margin-top: 38px;">
            Authorised Signatory
        </p>
    </div>
</div>
""",
    },

    "TPL_PSD_RETURN_REQUEST": {
        "status": "Draft",
        "filename": (
            "PSD_RETURN_REQUEST_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "required_fields": COMMON_REQUIRED_FIELDS,
        "html": BASE_STYLE + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            PARASRAMKA ENGINEERING PRIVATE LIMITED
        </div>
        <div class="pepl-title">
            Security Deposit / Bank Guarantee Return Request
        </div>
    </div>

    <table class="pepl-meta">
        <tr>
            <td>
                <strong>Reference:</strong> {{ source_document }}
            </td>
            <td style="text-align: right;">
                <strong>Date:</strong> {{ today }}
            </td>
        </tr>
    </table>

    <p>
        To,<br>
        <strong>
            {{ selected_psd_entry.beneficiary_name
                or customer
                or "The Concerned Authority" }}
        </strong><br>
        {{ selected_psd_entry.beneficiary_address or "" }}
    </p>

    <p>
        <strong>
            Subject: Request for Release / Return of Security
            Deposit or Bank Guarantee
        </strong>
    </p>

    <p>
        Dear Sir/Madam,
    </p>

    <p>
        With reference to Sales Order
        <strong>{{ sales_order.name or "-" }}</strong>,
        we request release or return of the security instrument
        detailed below, subject to completion of all contractual and
        departmental requirements.
    </p>

    <table class="pepl-table">
        <tr>
            <th>Security Mode</th>
            <td>
                {{ selected_psd_entry.security_mode or "-" }}
            </td>
        </tr>
        <tr>
            <th>Bank Guarantee Number</th>
            <td>{{ selected_psd_entry.bg_number or "-" }}</td>
        </tr>
        <tr>
            <th>Amount</th>
            <td>{{ selected_psd_entry.bg_amount or "-" }}</td>
        </tr>
        <tr>
            <th>Expiry Date</th>
            <td>
                {{ selected_psd_entry.bg_expiry_date or "-" }}
            </td>
        </tr>
    </table>

    <p>
        Kindly process the release and provide the applicable
        acknowledgement or no-objection confirmation.
    </p>

    <div class="pepl-signature">
        <p>
            For Parasramka Engineering Private Limited
        </p>
        <p style="margin-top: 38px;">
            Authorised Signatory
        </p>
    </div>
</div>
""",
    },

    "TPL_PSD_BG_APPLICATION": {
        "status": "Draft",
        "filename": (
            "PSD_BG_APPLICATION_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "required_fields": COMMON_REQUIRED_FIELDS,
        "html": BASE_STYLE + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            PARASRAMKA ENGINEERING PRIVATE LIMITED
        </div>
        <div class="pepl-title">
            Bank Guarantee Application Data Sheet
        </div>
    </div>

    <p>
        This controlled data sheet records the ERP source values
        required for preparation of the issuing bank's prescribed
        Bank Guarantee application form.
    </p>

    <table class="pepl-table">
        <tr>
            <th>Beneficiary</th>
            <td>
                {{ selected_psd_entry.beneficiary_name or "-" }}
            </td>
        </tr>
        <tr>
            <th>Beneficiary Address</th>
            <td>
                {{ selected_psd_entry.beneficiary_address or "-" }}
            </td>
        </tr>
        <tr>
            <th>Sales Order</th>
            <td>{{ sales_order.name or "-" }}</td>
        </tr>
        <tr>
            <th>Guarantee Amount</th>
            <td>{{ selected_psd_entry.bg_amount or "-" }}</td>
        </tr>
        <tr>
            <th>Expiry Date</th>
            <td>
                {{ selected_psd_entry.bg_expiry_date or "-" }}
            </td>
        </tr>
        <tr>
            <th>Claim Expiry Date</th>
            <td>
                {{ selected_psd_entry.claim_expiry_date or "-" }}
            </td>
        </tr>
        <tr>
            <th>Issuing Bank</th>
            <td>
                {{ selected_psd_entry.issuing_bank or "-" }}
            </td>
        </tr>
        <tr>
            <th>Branch</th>
            <td>
                {{ selected_psd_entry.issuing_bank_branch or "-" }}
            </td>
        </tr>
    </table>

    <div class="pepl-note">
        The final bank application must use the current form and
        conditions prescribed by the issuing bank.
    </div>
</div>
""",
    },

    "TPL_PSD_BG_TEXT": {
        "status": "Draft",
        "filename": (
            "PSD_BG_TEXT_"
            "{{ source_document }}_"
            "R{{ revision }}.pdf"
        ),
        "required_fields": COMMON_REQUIRED_FIELDS,
        "html": BASE_STYLE + """
<div class="pepl-document">
    <div class="pepl-header">
        <div class="pepl-company">
            PARASRAMKA ENGINEERING PRIVATE LIMITED
        </div>
        <div class="pepl-title">
            Bank Guarantee Text / Annexure Control Sheet
        </div>
    </div>

    <p>
        This record identifies the commercial and reference values
        associated with the controlled Bank Guarantee text.
    </p>

    <table class="pepl-table">
        <tr>
            <th>Beneficiary</th>
            <td>
                {{ selected_psd_entry.beneficiary_name or "-" }}
            </td>
        </tr>
        <tr>
            <th>Sales Order</th>
            <td>{{ sales_order.name or "-" }}</td>
        </tr>
        <tr>
            <th>Bank Guarantee Number</th>
            <td>{{ selected_psd_entry.bg_number or "-" }}</td>
        </tr>
        <tr>
            <th>Amount</th>
            <td>{{ selected_psd_entry.bg_amount or "-" }}</td>
        </tr>
        <tr>
            <th>Expiry Date</th>
            <td>
                {{ selected_psd_entry.bg_expiry_date or "-" }}
            </td>
        </tr>
        <tr>
            <th>Claim Expiry Date</th>
            <td>
                {{ selected_psd_entry.claim_expiry_date or "-" }}
            </td>
        </tr>
    </table>

    <div class="pepl-note">
        The operative legal Bank Guarantee wording must be the
        version approved by the beneficiary and accepted by the
        issuing bank. This control sheet does not replace that
        approved legal wording.
    </div>
</div>
""",
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
            values["required_fields"]
        )
        template.output_filename_pattern = values[
            "filename"
        ]
        template.active = 1
        template.status = values["status"]
        template.requires_manual_review = 1

        template.notes = (
            "PSD/BG controlled template configured through "
            "source-controlled application patch. Draft templates "
            "require client or bank content approval before use."
        )

        template.save(
            ignore_permissions=True
        )

    frappe.clear_cache(
        doctype="PEPL Standard Document Template"
    )
