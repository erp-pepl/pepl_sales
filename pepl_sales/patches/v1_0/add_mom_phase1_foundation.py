import frappe

from pepl_sales.setup.mom_phase1 import ensure_foundation, ensure_roles


def execute():
    ensure_roles()

    for doctype in (
        "pepl_vendor_approval_requirement",
        "pepl_document_requirement",
        "pepl_standard_document_template",
        "pepl_generated_document_item",
        "pepl_generated_document",
        "pepl_vendor_product_supply_history",
    ):
        frappe.reload_doc("pepl_sales", "doctype", doctype, force=True)

    custom_permissions = frappe.db.count("Custom DocPerm", {"parent": "PEPL Tender"})
    ensure_foundation(reset_permissions=not bool(custom_permissions))

    if custom_permissions:
        frappe.log_error(
            "PEPL Tender permissions were not reset because Custom DocPerm rows exist. "
            "Review and apply the three PEPL Tender roles manually or with a controlled script.",
            "PEPL MoM Phase 1 Permission Review",
        )
