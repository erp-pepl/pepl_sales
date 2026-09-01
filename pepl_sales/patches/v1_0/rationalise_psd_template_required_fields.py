import json

import frappe


# The PSD/BG templates inherited one shared required-field list that
# demanded every bank-guarantee attribute. In practice each letter is
# prepared at a different point in the PSD lifecycle, and each HTML
# template already renders "-" for any value that is absent.
#
# Requiring data that does not exist yet - or that never exists for a
# cash security deposit - blocks legitimate documents. The controlling
# safeguard is the Draft/Reviewed/Issued lifecycle plus
# requires_manual_review, not this list.
#
# Each template now requires only the values without which the letter
# would be meaningless.

BASE_FIELDS = [
    "source_doctype",
    "source_document",
    "customer",
    "sales_order.name",
    "selected_psd_entry.name",
]


REQUIRED_FIELDS = {
    # Submits a guarantee that already exists, so the guarantee must
    # be identified and the beneficiary named.
    "TPL_PSD_BG_SUBMISSION_COVER": BASE_FIELDS + [
        "selected_psd_entry.beneficiary_name",
        "selected_psd_entry.bg_number",
    ],

    # Addressed to the issuing bank to collect a prepared guarantee.
    # The bank must be identified; the guarantee may not be numbered
    # until collection.
    "TPL_PSD_BG_COLLECTION_AUTHORITY": BASE_FIELDS + [
        "selected_psd_entry.issuing_bank",
        "selected_psd_entry.beneficiary_name",
    ],

    # Requests release of the security. Valid for a bank guarantee AND
    # for a cash security deposit, so no BG-specific field is required.
    "TPL_PSD_RETURN_REQUEST": BASE_FIELDS + [
        "selected_psd_entry.security_mode",
        "selected_psd_entry.beneficiary_name",
    ],

    # Not approved for issue, but kept consistent for the day the
    # bank-approved wording is supplied.
    "TPL_PSD_BG_TEXT": BASE_FIELDS + [
        "selected_psd_entry.beneficiary_name",
    ],
}


def execute():
    if not frappe.db.exists(
        "DocType",
        "PEPL Standard Document Template",
    ):
        return

    for code, fields in REQUIRED_FIELDS.items():
        if not frappe.db.exists(
            "PEPL Standard Document Template",
            code,
        ):
            continue

        frappe.db.set_value(
            "PEPL Standard Document Template",
            code,
            "required_source_fields",
            json.dumps(fields),
            update_modified=False,
        )

    frappe.clear_cache(
        doctype="PEPL Standard Document Template"
    )
