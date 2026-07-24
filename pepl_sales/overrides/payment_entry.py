import frappe
from frappe import _
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

    if (
        lower_mode == "dd"
        or "demand draft" in lower_mode
    ):
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

    # Recovery path for historical invoices for which the tracker
    # was not created when the invoice was originally submitted.
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
    PEPL Cycle 1 currently expects INR/same-currency receipts.

    Do not silently create incorrect bank-credit amounts for a
    cross-currency Payment Entry.
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


def sync_payment_entry(payment_entry):
    """
    Synchronize one submitted ERPNext Payment Entry into PEPL Payment Tracker.

    One Payment Entry may contain multiple Sales Invoice references.
    Synchronization therefore happens per Payment Entry Reference row.
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

    if not invoice_references:
        return {
            "synced": False,
            "reason": "No Sales Invoice references exist.",
        }

    total_positive_allocated = sum(
        flt(row.allocated_amount)
        for row in positive_references
    )

    if total_positive_allocated <= 0:
        return {
            "synced": False,
            "reason": "No positive allocation exists.",
        }

    # For incoming same-currency payments, received_amount is the actual
    # amount credited to the destination bank/cash account.
    actual_bank_credit = flt(
        payment_entry.received_amount
        or payment_entry.paid_amount
    )

    # Do not assign unallocated customer advances to invoice trackers.
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
                    "Cross-currency Payment Entry requires an explicit "
                    "PEPL currency-allocation policy."
                ),
            })
            continue

        tracker = _get_or_create_tracker(invoice.name)

        allocated_amount = flt(
            reference.allocated_amount
        )

        bank_credit_share = flt(
            bank_credit_for_allocations
            * allocated_amount
            / total_positive_allocated,
            2,
        )

        existing_row = None

        for row in tracker.payment_receipts or []:
            if (
                row.payment_entry == payment_entry.name
                and row.payment_entry_reference == reference.name
            ):
                existing_row = row
                break

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
        else:
            tracker.append(
                "payment_receipts",
                values,
            )

        tracker.save(ignore_permissions=True)

        synced.append({
            "invoice": invoice.name,
            "tracker": tracker.name,
            "allocated_amount": allocated_amount,
            "bank_credit": bank_credit_share,
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
    }


def unsync_payment_entry(payment_entry):
    """
    Remove auto-synced PEPL receipt rows when a Payment Entry is cancelled.

    Manual receipt rows are never deleted.
    """

    receipt_rows = frappe.get_all(
        "PEPL Payment Receipt",
        filters={
            "payment_entry": payment_entry.name,
            "auto_synced": 1,
        },
        fields=[
            "name",
            "parent",
        ],
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

        remaining_receipts = [
            row
            for row in tracker.payment_receipts or []
            if flt(row.amount_received) > 0
        ]

        # A Payment Entry cancellation must be capable of moving the
        # operational state backwards.
        if (
            not remaining_receipts
            and tracker.payment_status
            in {"Payment Received", "Reconciled"}
        ):
            tracker.payment_status = "Bills Submitted"

        tracker.save(ignore_permissions=True)

        updated.append(tracker.name)

    return {
        "payment_entry": payment_entry.name,
        "trackers_updated": updated,
        "receipts_removed": len(receipt_rows),
    }
