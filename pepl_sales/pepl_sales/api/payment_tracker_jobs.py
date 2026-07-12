import frappe
from frappe.utils import date_diff, flt, getdate, today


CLOSED_STATUSES = {"Reconciled", "Closed"}


def update_all_payment_trackers_daily():
    """
    Recalculate ageing for open PEPL Payment Trackers.

    Ageing follows the Payment Tracker DocType options:
    - 0-30 days
    - 31-45 days
    - 45+ days (MSME breach)

    Fully realised, reconciled and closed trackers are reset to zero ageing.
    """

    trackers = frappe.get_all(
        "PEPL Payment Tracker",
        fields=[
            "name",
            "invoice_date",
            "payment_status",
            "total_outstanding",
        ],
        limit_page_length=0,
    )

    current_date = getdate(today())
    updated = 0
    reset = 0
    skipped = 0
    failures = []

    for tracker in trackers:
        try:
            payment_status = tracker.payment_status or ""
            outstanding = flt(tracker.total_outstanding)

            if (
                payment_status in CLOSED_STATUSES
                or outstanding <= 0
            ):
                frappe.db.set_value(
                    "PEPL Payment Tracker",
                    tracker.name,
                    {
                        "days_outstanding": 0,
                        "ageing_bucket": "0-30 days",
                        "last_update_date": current_date,
                    },
                    update_modified=False,
                )
                reset += 1
                continue

            if not tracker.invoice_date:
                skipped += 1
                continue

            days_outstanding = max(
                date_diff(
                    current_date,
                    getdate(tracker.invoice_date),
                ),
                0,
            )

            if days_outstanding <= 30:
                ageing_bucket = "0-30 days"
            elif days_outstanding <= 45:
                ageing_bucket = "31-45 days"
            else:
                ageing_bucket = "45+ days (MSME breach)"

            frappe.db.set_value(
                "PEPL Payment Tracker",
                tracker.name,
                {
                    "days_outstanding": days_outstanding,
                    "ageing_bucket": ageing_bucket,
                    "last_update_date": current_date,
                },
                update_modified=False,
            )

            updated += 1

        except Exception:
            failures.append(tracker.name)

            frappe.log_error(
                frappe.get_traceback(),
                "PEPL Payment Tracker Daily Ageing Failure",
            )

    return {
        "updated": updated,
        "reset": reset,
        "skipped": skipped,
        "failed": len(failures),
        "failed_trackers": failures,
    }
