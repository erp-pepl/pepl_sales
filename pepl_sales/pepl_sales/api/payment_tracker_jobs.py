import frappe
from frappe.utils import date_diff, today, getdate


def update_all_payment_trackers_daily():
    open_trackers = frappe.get_all(
        "PEPL Payment Tracker",
        filters={"payment_status": ["not in", ["Reconciled", "Closed", "Cancelled"]]},
        fields=["name", "invoice_date"]
    )

    for tracker in open_trackers:
        if not tracker.invoice_date:
            continue

        days = date_diff(today(), getdate(tracker.invoice_date))

        if days <= 30:
            bucket = "0-30 days"
        elif days <= 60:
            bucket = "31-60 days"
        elif days <= 90:
            bucket = "61-90 days"
        else:
            bucket = "90+ days"

        frappe.db.set_value(
            "PEPL Payment Tracker",
            tracker.name,
            {
                "days_outstanding": days,
                "ageing_bucket": bucket,
                "last_update_date": today()
            }
        )
