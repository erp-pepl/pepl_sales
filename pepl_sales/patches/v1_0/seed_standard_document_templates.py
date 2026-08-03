import json

import frappe


TEMPLATES = [
    {
        "code": "TPL_PSD_BG_COLLECTION_AUTHORITY",
        "name": "Authority Letter for Collection of BG",
        "requirement": "PSD_BG_COLLECTION_AUTHORITY",
        "format": "PDF",
    },
    {
        "code": "TPL_PSD_BG_SUBMISSION_COVER",
        "name": "BG Submission Covering Letter",
        "requirement": "PSD_BG_SUBMISSION_COVER",
        "format": "PDF",
    },
    {
        "code": "TPL_CONTRACTOR_BILL",
        "name": "Contractor's Bill",
        "requirement": "CONTRACTOR_BILL",
        "format": "PDF",
    },
    {
        "code": "TPL_BULK_LOT_OFFER",
        "name": "Bulk Lot Offer to Consignee",
        "requirement": "BULK_LOT_OFFER",
        "format": "PDF",
    },
    {
        "code": "TPL_DISPATCH_LABEL",
        "name": "Dispatch Label / Sticker",
        "requirement": "DISPATCH_LABEL",
        "format": "Label",
    },
    {
        "code": "TPL_DRAWING_SPEC_REQUEST",
        "name": "Drawing and Specification Request",
        "requirement": "DRAWING_SPEC_REQUEST",
        "format": "PDF",
    },
    {
        "code": "TPL_PROOF_SCHEDULE_REQUEST",
        "name": "Proof Schedule Request",
        "requirement": "PROOF_SCHEDULE_REQUEST",
        "format": "PDF",
    },
    {
        "code": "TPL_LOT_NUMBER_REQUEST",
        "name": "Lot Number and Lot Size Request",
        "requirement": "LOT_NUMBER_REQUEST",
        "format": "PDF",
    },
    {
        "code": "TPL_NABL_TEST_OFFER",
        "name": "Material Offer to NABL Test Laboratory",
        "requirement": "NABL_TEST_OFFER",
        "format": "PDF",
    },
    {
        "code": "TPL_PAYMENT_REQUEST",
        "name": "Payment Request Letter",
        "requirement": "PAYMENT_REQUEST",
        "format": "PDF",
    },
    {
        "code": "TPL_WORK_TEST_CERTIFICATE",
        "name": "Work Test Certificate",
        "requirement": "WORK_TEST_CERTIFICATE",
        "format": "PDF",
    },
    {
        "code": "TPL_PSD_RETURN_REQUEST",
        "name": "PSD / Security Deposit Return Request",
        "requirement": "PSD_RETURN_REQUEST",
        "format": "PDF",
    },
    {
        "code": "TPL_PSD_BG_APPLICATION",
        "name": "Bank Guarantee Application Form",
        "requirement": "PSD_BG_APPLICATION",
        "format": "PDF",
    },
    {
        "code": "TPL_PSD_BG_DEBIT_AUTHORITY",
        "name": "BG Request-cum-Debit Authority Letter",
        "requirement": "PSD_BG_DEBIT_AUTHORITY",
        "format": "PDF",
    },
    {
        "code": "TPL_PSD_BG_TEXT",
        "name": "Bank Guarantee Text / Annexure",
        "requirement": "PSD_BG_TEXT",
        "format": "PDF",
    },
    {
        "code": "TPL_QUALITY_SELF_CERTIFICATE",
        "name": "Quality Self-Certificate",
        "requirement": "QUALITY_SELF_CERTIFICATE",
        "format": "PDF",
    },
    {
        "code": "TPL_RAW_MATERIAL_OFFER",
        "name": "Raw Material Offer",
        "requirement": "RAW_MATERIAL_OFFER",
        "format": "PDF",
    },
    {
        "code": "TPL_GST_CERTIFICATE",
        "name": "GST Certificate",
        "requirement": "GST_CERTIFICATE",
        "format": "PDF",
    },
    {
        "code": "TPL_GST_SUMMARY",
        "name": "GST Summary",
        "requirement": "GST_SUMMARY",
        "format": "PDF",
    },
    {
        "code": "TPL_GUARANTEE_CERTIFICATE",
        "name": "After-Invoice Guarantee Certificate",
        "requirement": "GUARANTEE_CERTIFICATE",
        "format": "PDF",
    },
]


def execute():
    if not frappe.db.exists(
        "DocType",
        "PEPL Standard Document Template",
    ):
        return

    for row in TEMPLATES:
        if not frappe.db.exists(
            "PEPL Document Requirement",
            row["requirement"],
        ):
            frappe.throw(
                "Document Requirement {0} is missing."
                .format(row["requirement"])
            )

        values = {
            "template_name": row["name"],
            "document_requirement":
                row["requirement"],
            "sector": "Common",
            "output_format": row["format"],
            "template_engine": "HTML Print",
            "letterhead_version": "PEPL-V1",
            "template_version": "1.0",
            "status": "Draft",
            "active": 1,
            "output_filename_pattern": (
                row["requirement"]
                + "_{{ source_document }}"
                + "_R{{ revision }}.pdf"
            ),
            "required_source_fields":
                json.dumps(
                    [
                        "source_doctype",
                        "source_document",
                        "customer",
                    ]
                ),
            "requires_manual_review": 1,
            "requires_signature": 0,
            "requires_stamp": 0,
            "notes": (
                "Foundation template created by the "
                "PEPL Standard Document Generation patch. "
                "Approve only after the controlled layout "
                "and source mappings are validated."
            ),
        }

        if frappe.db.exists(
            "PEPL Standard Document Template",
            row["code"],
        ):
            doc = frappe.get_doc(
                "PEPL Standard Document Template",
                row["code"],
            )

            for fieldname, value in values.items():
                doc.set(fieldname, value)

            doc.save(ignore_permissions=True)

        else:
            doc = frappe.get_doc({
                "doctype":
                    "PEPL Standard Document Template",
                "template_code": row["code"],
                **values,
            })

            doc.insert(ignore_permissions=True)

    frappe.clear_cache(
        doctype="PEPL Standard Document Template"
    )
