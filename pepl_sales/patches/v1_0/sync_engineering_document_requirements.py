import frappe

from pepl_sales.pepl_sales.doctype.pepl_document_tracker.document_requirement_sync import (
    synchronize_engineering_requirements,
)
from pepl_sales.pepl_sales.doctype.pepl_document_tracker.pepl_document_tracker import (
    _get_sector_for_sales_order,
)


def execute():
    if not frappe.db.exists(
        "DocType",
        "PEPL Document Tracker",
    ):
        return

    tracker_names = frappe.get_all(
        "PEPL Document Tracker",
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    )

    for tracker_name in tracker_names:
        tracker = frappe.get_doc(
            "PEPL Document Tracker",
            tracker_name,
        )

        if not tracker.linked_sales_order:
            continue

        if not frappe.db.exists(
            "Sales Order",
            tracker.linked_sales_order,
        ):
            continue

        sales_order = frappe.get_doc(
            "Sales Order",
            tracker.linked_sales_order,
        )

        sector = _get_sector_for_sales_order(
            sales_order
        )

        result = (
            synchronize_engineering_requirements(
                tracker,
                sales_order,
                sector,
            )
        )

        if (
            result["created"]
            or result["updated"]
            or result["historical"]
        ):
            tracker.save(
                ignore_permissions=True
            )

    frappe.clear_cache(
        doctype="PEPL Document Tracker"
    )
