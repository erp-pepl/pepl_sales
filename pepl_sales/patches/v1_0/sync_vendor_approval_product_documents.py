import frappe

from pepl_sales.pepl_sales.doctype.vendor_approval_status.vendor_approval_sync import (
    synchronize_requirement_rows,
)


def execute():
    if not frappe.db.exists(
        "DocType",
        "Vendor Approval Status",
    ):
        return

    if not frappe.db.exists(
        "DocType",
        "PEPL Product Master",
    ):
        return

    names = frappe.get_all(
        "Vendor Approval Status",
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    )

    for name in names:
        doc = frappe.get_doc(
            "Vendor Approval Status",
            name,
        )

        synchronize_requirement_rows(doc)
        doc.save(ignore_permissions=True)

    frappe.clear_cache(
        doctype="Vendor Approval Status"
    )
