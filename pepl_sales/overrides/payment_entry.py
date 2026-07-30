import frappe
from frappe.utils import flt


def _normalise_payment_mode(mode_of_payment):
    """Map ERPNext Mode of Payment values to PEPL receipt options."""

    mode = (mode_of_payment or "").strip()
    lower_mode = mode.lower()

    if lower_mode == "rtgs":
        return "RTGS"

    if lower_mode == "neft":
        return "NEFT"

    if "cheque" in lower_mode or "check" in lower_mode:
        return "Cheque"

    if lower_mode == "cash":
        return "Cash"

    if lower_mode == "dd" or "demand draft" in lower_mode:
        return "DD"

    if any(
        keyword in lower_mode
        for keyword in [
            "online",
            "wire",
            "bank transfer",
            "upi",
            "imps",
        ]
    ):
        return "Online Transfer"

    return "Other"


def _get_or_create_tracker(invoice_name):
    tracker_name = frappe.db.exists(
        "PEPL Payment Tracker",
        {"linked_sales_invoice": invoice_name},
    )

    if tracker_name:
        return frappe.get_doc(
            "PEPL Payment Tracker",
            tracker_name,
        )

    from pepl_sales.pepl_sales.doctype.pepl_payment_tracker.pepl_payment_tracker import (
        create_payment_tracker_for_invoice,
    )

    result = create_payment_tracker_for_invoice(invoice_name)

    return frappe.get_doc(
        "PEPL Payment Tracker",
        result["tracker_name"],
    )


def _validate_currency_context(payment_entry, invoice):
    """
    PEPL Cycle 1 currently expects same-currency receipts.
    """

    currencies = {
        value
        for value in [
            payment_entry.paid_from_account_currency,
            payment_entry.paid_to_account_currency,
            invoice.currency,
        ]
        if value
    }

    return len(currencies) <= 1


def _get_existing_auto_synced_rows(payment_entry_name):
    """
    Return all PEPL auto-synced receipt rows for one Payment Entry.
    """

    return frappe.get_all(
        "PEPL Payment Receipt",
        filters={
            "payment_entry": payment_entry_name,
            "auto_synced": 1,
        },
        fields=[
            "name",
            "parent",
            "payment_entry_reference",
        ],
        limit_page_length=0,
    )


def _remove_stale_rows(payment_entry, current_reference_ids):
    """
    Remove PEPL receipt rows whose ERPNext Payment Entry Reference
    no longer exists.

    Manual receipt rows are never removed.
    """

    existing_rows = _get_existing_auto_synced_rows(
        payment_entry.name
    )

    tracker_names = sorted({
        row.parent
        for row in existing_rows
        if (
            row.parent
            and row.payment_entry_reference
            not in current_reference_ids
        )
    })

    removed = []
    updated_trackers = []

    for tracker_name in tracker_names:
        tracker = frappe.get_doc(
            "PEPL Payment Tracker",
            tracker_name,
        )

        rows_to_remove = [
            row
            for row in tracker.payment_receipts or []
            if (
                row.auto_synced
                and row.payment_entry == payment_entry.name
                and row.payment_entry_reference
                not in current_reference_ids
            )
        ]

        for row in rows_to_remove:
            removed.append({
                "tracker": tracker.name,
                "receipt": row.name,
                "payment_entry_reference":
                    row.payment_entry_reference,
            })

            tracker.remove(row)

        if rows_to_remove:
            tracker.save(ignore_permissions=True)
            updated_trackers.append(tracker.name)

    return {
        "removed": removed,
        "trackers_updated": updated_trackers,
    }


def sync_payment_entry(payment_entry):
    """
    Synchronize one submitted ERPNext Payment Entry into PEPL.

    This method supports:
    - initial Payment Entry submission;
    - Payment Reconciliation;
    - UnReconcile;
    - repeated idempotent synchronization.
    """

    if payment_entry.docstatus != 1:
        return {
            "synced": False,
            "reason": "Payment Entry is not submitted.",
        }

    if payment_entry.payment_type != "Receive":
        return {
            "synced": False,
            "reason": "Only incoming Payment Entries are relevant.",
        }

    if payment_entry.party_type != "Customer":
        return {
            "synced": False,
            "reason": "Payment Entry party is not a Customer.",
        }

    positive_references = [
        row
        for row in payment_entry.references or []
        if flt(row.allocated_amount) > 0
    ]

    invoice_references = [
        row
        for row in positive_references
        if row.reference_doctype == "Sales Invoice"
    ]

    current_reference_ids = {
        row.name
        for row in invoice_references
        if row.name
    }

    cleanup_result = _remove_stale_rows(
        payment_entry,
        current_reference_ids,
    )

    if not invoice_references:
        return {
            "synced": False,
            "payment_entry": payment_entry.name,
            "reason": "No Sales Invoice references exist.",
            "cleanup": cleanup_result,
        }

    total_positive_allocated = sum(
        flt(row.allocated_amount)
        for row in positive_references
    )

    if total_positive_allocated <= 0:
        return {
            "synced": False,
            "payment_entry": payment_entry.name,
            "reason": "No positive allocation exists.",
            "cleanup": cleanup_result,
        }

    actual_bank_credit = flt(
        payment_entry.received_amount
        or payment_entry.paid_amount
    )

    bank_credit_for_allocations = min(
        actual_bank_credit,
        total_positive_allocated,
    )

    synced = []
    skipped = []

    for reference in invoice_references:
        invoice = frappe.get_doc(
            "Sales Invoice",
            reference.reference_name,
        )

        if not _validate_currency_context(
            payment_entry,
            invoice,
        ):
            skipped.append({
                "invoice": invoice.name,
                "reason": (
                    "Cross-currency Payment Entry requires an "
                    "explicit PEPL allocation policy."
                ),
            })
            continue

        tracker = _get_or_create_tracker(invoice.name)

        allocated_amount = flt(
            reference.allocated_amount
        )

        bank_credit_share = flt(
            (
                bank_credit_for_allocations
                * allocated_amount
                / total_positive_allocated
            ),
            2,
        )

        matching_rows = [
            row
            for row in tracker.payment_receipts or []
            if (
                row.payment_entry == payment_entry.name
                and row.payment_entry_reference
                == reference.name
                and row.auto_synced
            )
        ]

        existing_row = (
            matching_rows[0]
            if matching_rows
            else None
        )

        duplicate_rows = matching_rows[1:]

        for duplicate_row in duplicate_rows:
            tracker.remove(duplicate_row)

        values = {
            "payment_date": payment_entry.posting_date,
            "amount_received": bank_credit_share,
            "payment_mode": _normalise_payment_mode(
                payment_entry.mode_of_payment
            ),
            "payment_reference": (
                payment_entry.reference_no
                or payment_entry.name
            ),
            "bank": payment_entry.paid_to or "",
            "payment_entry": payment_entry.name,
            "payment_entry_reference": reference.name,
            "allocated_amount": allocated_amount,
            "auto_synced": 1,
            "remarks": (
                "Auto-synced from ERPNext Payment Entry "
                f"{payment_entry.name}. "
                f"Invoice allocation: {allocated_amount}."
            ),
        }

        if existing_row:
            for fieldname, value in values.items():
                existing_row.set(fieldname, value)

            action = "updated"

        else:
            tracker.append(
                "payment_receipts",
                values,
            )

            action = "inserted"

        tracker.save(ignore_permissions=True)

        synced.append({
            "invoice": invoice.name,
            "tracker": tracker.name,
            "action": action,
            "allocated_amount": allocated_amount,
            "bank_credit": bank_credit_share,
            "duplicates_removed": len(duplicate_rows),
        })

    if skipped:
        frappe.log_error(
            message=frappe.as_json({
                "payment_entry": payment_entry.name,
                "skipped": skipped,
            }),
            title="PEPL Payment Entry Sync Warning",
        )

    return {
        "synced": bool(synced),
        "payment_entry": payment_entry.name,
        "rows": synced,
        "skipped": skipped,
        "cleanup": cleanup_result,
    }


def unsync_payment_entry(payment_entry):
    """
    Remove all auto-synced PEPL receipt rows when a Payment Entry
    is cancelled.

    Manual receipt rows are never deleted.
    """

    receipt_rows = _get_existing_auto_synced_rows(
        payment_entry.name
    )

    tracker_names = sorted({
        row.parent
        for row in receipt_rows
        if row.parent
    })

    updated = []

    for tracker_name in tracker_names:
        tracker = frappe.get_doc(
            "PEPL Payment Tracker",
            tracker_name,
        )

        rows_to_remove = [
            row
            for row in tracker.payment_receipts or []
            if (
                row.payment_entry == payment_entry.name
                and row.auto_synced
            )
        ]

        for row in rows_to_remove:
            tracker.remove(row)

        if rows_to_remove:
            tracker.save(ignore_permissions=True)
            updated.append(tracker.name)

    return {
        "payment_entry": payment_entry.name,
        "trackers_updated": updated,
        "receipts_removed": len(receipt_rows),
    }
