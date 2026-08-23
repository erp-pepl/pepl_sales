import frappe


def execute():
    """
    Permanently make Sales Invoice document requirements advisory.

    Existing tracker evidence, status, dates and attachments are preserved.
    Only the historical Sales Invoice blocking flag is neutralized.
    """

    if frappe.db.exists(
        "DocType",
        "PEPL Document Requirement",
    ):
        requirements = frappe.get_all(
            "PEPL Document Requirement",
            filters={
                "blocking_event":
                    "Sales Invoice",
            },
            pluck="name",
            limit_page_length=0,
        )

        for name in requirements:
            frappe.db.set_value(
                "PEPL Document Requirement",
                name,
                "blocking_event",
                "None",
                update_modified=False,
            )

    if frappe.db.exists(
        "DocType",
        "PEPL Document Entry",
    ):
        entries = frappe.get_all(
            "PEPL Document Entry",
            filters={
                "blocking_event":
                    "Sales Invoice",
            },
            pluck="name",
            limit_page_length=0,
        )

        for name in entries:
            frappe.db.set_value(
                "PEPL Document Entry",
                name,
                "blocking_event",
                "None",
                update_modified=False,
            )

    frappe.clear_cache(
        doctype="PEPL Document Requirement"
    )

    frappe.clear_cache(
        doctype="PEPL Document Tracker"
    )
