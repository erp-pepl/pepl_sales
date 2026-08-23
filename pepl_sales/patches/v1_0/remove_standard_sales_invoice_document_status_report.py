import frappe


OLD_STANDARD_REPORT = (
    "PEPL Sales Invoice Document Status"
)

CUSTOM_UI_REPORT = (
    "PEPL Sales Invoice Doc Status"
)


def execute():
    """
    Remove the retired app-backed Sales Invoice document-status report.

    The replacement report is a site-level custom Script Report named
    'PEPL Sales Invoice Doc Status'. It must never be modified or deleted
    by this migration.
    """

    # Absolute safety guard: the custom UI report must never be the
    # target of this migration.
    if OLD_STANDARD_REPORT == CUSTOM_UI_REPORT:
        frappe.throw(
            "Standard and custom report names unexpectedly match."
        )

    if not frappe.db.exists(
        "Report",
        OLD_STANDARD_REPORT,
    ):
        return

    report = frappe.get_doc(
        "Report",
        OLD_STANDARD_REPORT,
    )

    # This migration is only allowed to delete the retired standard
    # app report. If the record has somehow become a custom report,
    # leave it untouched rather than deleting user-managed content.
    if report.is_standard != "Yes":
        return

    frappe.delete_doc(
        "Report",
        OLD_STANDARD_REPORT,
        ignore_permissions=True,
        force=True,
    )

    frappe.clear_cache()
