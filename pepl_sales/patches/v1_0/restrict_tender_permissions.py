import frappe
from frappe.permissions import reset_perms


def execute():
    doctype_name = "PEPL Tender"

    if not frappe.db.exists(
        "DocType",
        doctype_name,
    ):
        return

    # Reload the source-controlled permission matrix from the
    # DocType JSON and replace the site's existing DocPerm rows.
    reset_perms(doctype_name)

    frappe.clear_cache(
        doctype=doctype_name
    )
