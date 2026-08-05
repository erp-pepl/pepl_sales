import frappe
from frappe import _


def validate_psd_tracker(doc, method=None):
    for row in doc.get("psd_entries") or []:
        _validate_psd_entry(row)


def _validate_psd_entry(row):
    if row.security_mode != "Bank Guarantee":
        return

    if row.bg_amount and row.bg_amount <= 0:
        frappe.throw(
            _(
                "BG Amount must be greater than zero "
                "in PSD Entry {0}."
            ).format(
                row.entry_label or row.idx
            )
        )

    if (
        row.claim_expiry_date
        and row.bg_expiry_date
        and row.claim_expiry_date
        < row.bg_expiry_date
    ):
        frappe.throw(
            _(
                "Claim Expiry Date cannot be before "
                "BG Expiry Date in PSD Entry {0}."
            ).format(
                row.entry_label or row.idx
            )
        )

    if row.final_bg_file:
        _validate_pdf_attachment(
            row.final_bg_file,
            "Final Bank Guarantee",
            row,
        )

    if row.bank_advice_file:
        _validate_pdf_attachment(
            row.bank_advice_file,
            "Bank Advice / Issuance Document",
            row,
        )


def _validate_pdf_attachment(
    file_url,
    field_label,
    row,
):
    file_doc = frappe.db.get_value(
        "File",
        {
            "file_url": file_url,
        },
        [
            "name",
            "file_name",
            "is_private",
            "file_size",
        ],
        as_dict=True,
    )

    if not file_doc:
        frappe.throw(
            _(
                "{0} file record was not found "
                "for PSD Entry {1}."
            ).format(
                field_label,
                row.entry_label or row.idx,
            )
        )

    file_name = (
        file_doc.file_name
        or file_url
        or ""
    ).lower()

    if not file_name.endswith(".pdf"):
        frappe.throw(
            _(
                "{0} must be a PDF file in "
                "PSD Entry {1}."
            ).format(
                field_label,
                row.entry_label or row.idx,
            )
        )

    if not file_doc.is_private:
        frappe.throw(
            _(
                "{0} must be stored as a private "
                "file in PSD Entry {1}."
            ).format(
                field_label,
                row.entry_label or row.idx,
            )
        )

    if not file_doc.file_size:
        frappe.throw(
            _(
                "{0} is empty in PSD Entry {1}."
            ).format(
                field_label,
                row.entry_label or row.idx,
            )
        )
