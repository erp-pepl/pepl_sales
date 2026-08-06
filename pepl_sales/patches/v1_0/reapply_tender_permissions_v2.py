import frappe
from frappe.permissions import reset_perms


def execute():
    doctype_name = "PEPL Tender"

    if not frappe.db.exists(
        "DocType",
        doctype_name,
    ):
        return

    reset_perms(doctype_name)

    frappe.clear_cache(
        doctype=doctype_name,
    )
