import json

import frappe


# Controlled templates whose layout and source mappings have been
# validated against the live system and which are released for
# operational use.
APPROVE_TEMPLATES = [
    "TPL_DRAWING_SPEC_REQUEST",
    "TPL_PROOF_SCHEDULE_REQUEST",
    "TPL_RAW_MATERIAL_OFFER",
    "TPL_QUALITY_SELF_CERTIFICATE",
    "TPL_NABL_TEST_OFFER",
    "TPL_LOT_NUMBER_REQUEST",
    "TPL_BULK_LOT_OFFER",
    "TPL_WORK_TEST_CERTIFICATE",
    "TPL_DISPATCH_LABEL",
    "TPL_GST_SUMMARY",
    "TPL_GUARANTEE_CERTIFICATE",
    "TPL_CONTRACTOR_BILL",
    "TPL_PAYMENT_REQUEST",
    "TPL_PSD_BG_APPLICATION",
    "TPL_PSD_BG_DEBIT_AUTHORITY",
    "TPL_PSD_BG_COLLECTION_AUTHORITY",
    "TPL_PSD_RETURN_REQUEST",
]


# Deliberately NOT approved:
#
# TPL_PSD_BG_TEXT
#     The operative legal guarantee wording must be the version
#     approved by the beneficiary and accepted by the issuing bank.
#     It is not PEPL's to release.
#
# TPL_GST_CERTIFICATE
#     Authority-issued evidence collected by PEPL, not a document
#     PEPL generates. It carries no HTML and is already inactive.


# Templates prepared BEFORE a Bank Guarantee exists cannot require
# post-issuance values such as bg_number or bg_expiry_date.
PRE_ISSUANCE_TEMPLATES = [
    "TPL_PSD_BG_APPLICATION",
    "TPL_PSD_BG_DEBIT_AUTHORITY",
]


PRE_ISSUANCE_REQUIRED_FIELDS = [
    "source_doctype",
    "source_document",
    "customer",
    "sales_order.name",
    "selected_psd_entry.name",
    "selected_psd_entry.beneficiary_name",
]


APPROVAL_NOTE = (
    "Released for operational use. Every generated document still "
    "passes through the Draft to Reviewed to Issued lifecycle, so a "
    "PEPL reviewer confirms the final wording before the document "
    "leaves the company. Wording changes are made by editing the "
    "HTML Template on this record and raising the Template Version."
)


def execute():
    if not frappe.db.exists(
        "DocType",
        "PEPL Standard Document Template",
    ):
        return

    # Relax pre-issuance requirements before approving, so the
    # templates become usable in the same migration.
    for code in PRE_ISSUANCE_TEMPLATES:
        if not frappe.db.exists(
            "PEPL Standard Document Template",
            code,
        ):
            continue

        frappe.db.set_value(
            "PEPL Standard Document Template",
            code,
            "required_source_fields",
            json.dumps(
                PRE_ISSUANCE_REQUIRED_FIELDS
            ),
            update_modified=False,
        )

    for code in APPROVE_TEMPLATES:
        if not frappe.db.exists(
            "PEPL Standard Document Template",
            code,
        ):
            continue

        doc = frappe.get_doc(
            "PEPL Standard Document Template",
            code,
        )

        if doc.status == "Approved":
            continue

        # Mirror the controller's own approval preconditions so this
        # patch can never create an unusable approved template.
        if (
            doc.template_engine == "HTML Print"
            and not doc.html_template
        ):
            continue

        if (
            doc.template_engine == "DOCX Template"
            and not doc.source_template_file
        ):
            continue

        doc.active = 1
        doc.status = "Approved"
        doc.notes = APPROVAL_NOTE

        doc.save(ignore_permissions=True)

    frappe.clear_cache(
        doctype="PEPL Standard Document Template"
    )
