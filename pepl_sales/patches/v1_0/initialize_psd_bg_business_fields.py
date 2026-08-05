import frappe


def execute():
    if not frappe.db.exists(
        "DocType",
        "PEPL PSD Entry",
    ):
        return

    rows = frappe.get_all(
        "PEPL PSD Entry",
        fields=[
            "name",
            "psd_status",
            "security_mode",
        ],
        limit_page_length=100000,
    )

    for row in rows:
        if row.security_mode:
            continue

        security_mode = (
            "Bank Guarantee"
            if row.psd_status in {
                "Requested to Bank",
                (
                    "Received from Bank / "
                    "Dispatched to Customer"
                ),
                "Active",
                "Letter to Bank for Closure",
            }
            else "Security Deposit"
        )

        frappe.db.set_value(
            "PEPL PSD Entry",
            row.name,
            "security_mode",
            security_mode,
            update_modified=False,
        )
