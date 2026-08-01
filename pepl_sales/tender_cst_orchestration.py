from __future__ import annotations

import frappe
from frappe import _


ACTIVE_CST_STATUSES = {
    "Draft",
    "Under Review",
    "Approved",
    "Used in Bid",
}

TERMINAL_TENDER_STATUSES = {
    "Submitted",
    "Won",
    "Partially Won",
    "Order Received",
    "Lost",
    "No Bid",
    "Cancelled",
    "Re-tendered",
}


def validate_cst_tender_linkage(doc, method=None):
    """Validate and populate CST linkage to one Tender Item.

    A linked CST belongs to one Tender Item, not merely to the Tender.
    Customer and Item are derived from the linked Tender and Tender Item.
    """

    linked_tender = (doc.linked_tender or "").strip()
    linked_tender_item = (
        doc.linked_tender_item or ""
    ).strip()

    if not linked_tender:
        if linked_tender_item:
            frappe.throw(
                _(
                    "Linked Tender is required when Linked Tender "
                    "Item Row is set."
                )
            )

        return

    if not linked_tender_item:
        frappe.throw(
            _(
                "Select the Linked Tender Item Row for Tender {0}."
            ).format(
                frappe.bold(linked_tender)
            )
        )

    if not frappe.db.exists(
        "PEPL Tender",
        linked_tender,
    ):
        frappe.throw(
            _("Linked Tender {0} does not exist.").format(
                frappe.bold(linked_tender)
            )
        )

    tender = frappe.get_doc(
        "PEPL Tender",
        linked_tender,
    )

    tender_item = _get_tender_item(
        tender,
        linked_tender_item,
    )

    if not tender_item:
        frappe.throw(
            _(
                "Tender Item Row {0} does not belong to "
                "Tender {1}."
            ).format(
                frappe.bold(linked_tender_item),
                frappe.bold(linked_tender),
            )
        )

    if not tender_item.item:
        frappe.throw(
            _(
                "Tender Item Row {0} has no Item."
            ).format(
                frappe.bold(linked_tender_item)
            )
        )

    doc.customer = tender.customer
    doc.linked_item = tender_item.item

    _validate_linked_product(
        doc,
        tender_item.item,
    )

    _validate_unique_active_cost_sheet(
        doc,
        linked_tender,
        linked_tender_item,
    )


def synchronize_cst_to_tender(doc, method=None):
    """Write CST linkage and price back to its Tender Item."""

    previous = doc.get_doc_before_save()

    previous_tender = None
    previous_item = None

    if previous:
        previous_tender = (
            previous.linked_tender or ""
        ).strip()
        previous_item = (
            previous.linked_tender_item or ""
        ).strip()

    current_tender = (
        doc.linked_tender or ""
    ).strip()
    current_item = (
        doc.linked_tender_item or ""
    ).strip()

    linkage_changed = (
        previous_tender != current_tender
        or previous_item != current_item
    )

    if (
        linkage_changed
        and previous_tender
        and previous_item
    ):
        _clear_tender_item_link(
            previous_tender,
            previous_item,
            doc.name,
        )

        _refresh_tender_costing_status(
            previous_tender
        )

    if not current_tender or not current_item:
        return

    tender = frappe.get_doc(
        "PEPL Tender",
        current_tender,
    )

    tender_item = _get_tender_item(
        tender,
        current_item,
    )

    if not tender_item:
        frappe.throw(
            _(
                "Tender Item Row {0} no longer belongs "
                "to Tender {1}."
            ).format(
                frappe.bold(current_item),
                frappe.bold(current_tender),
            )
        )

    tender_item.linked_cost_sheet = doc.name
    tender_item.our_bid_unit_price = (
        doc.final_bid_price or 0
    )

    _set_tender_costing_status(tender)

    tender.flags.ignore_version = True
    tender.save(ignore_permissions=True)


def clear_cst_from_tender(doc, method=None):
    """Clear Tender Item linkage when a CST is deleted."""

    linked_tender = (
        doc.linked_tender or ""
    ).strip()
    linked_tender_item = (
        doc.linked_tender_item or ""
    ).strip()

    if not linked_tender or not linked_tender_item:
        return

    _clear_tender_item_link(
        linked_tender,
        linked_tender_item,
        doc.name,
    )

    _refresh_tender_costing_status(
        linked_tender
    )


def _get_tender_item(tender, row_name):
    for row in tender.items or []:
        if row.name == row_name:
            return row

    return None


def _validate_linked_product(doc, item_code):
    if not doc.linked_product:
        products = frappe.get_all(
            "PEPL Product Master",
            filters={
                "linked_item": item_code,
                "status": "Active",
            },
            pluck="name",
            order_by="name asc",
            limit_page_length=0,
        )

        if len(products) == 1:
            doc.linked_product = products[0]

        return

    product_item = frappe.db.get_value(
        "PEPL Product Master",
        doc.linked_product,
        "linked_item",
    )

    if product_item != item_code:
        frappe.throw(
            _(
                "Linked Product {0} belongs to Item {1}, "
                "but the selected Tender Item is {2}."
            ).format(
                frappe.bold(doc.linked_product),
                frappe.bold(product_item or _("None")),
                frappe.bold(item_code),
            )
        )


def _validate_unique_active_cost_sheet(
    doc,
    tender_name,
    tender_item_name,
):
    filters = {
        "linked_tender": tender_name,
        "linked_tender_item": tender_item_name,
        "status": ["in", list(ACTIVE_CST_STATUSES)],
    }

    existing = frappe.get_all(
        "PEPL CST Cost Sheet",
        filters=filters,
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    )

    existing = [
        name
        for name in existing
        if name != doc.name
    ]

    if existing:
        frappe.throw(
            _(
                "Tender Item Row {0} already has an active "
                "Cost Sheet: {1}. Supersede or obsolete the "
                "existing Cost Sheet before creating another."
            ).format(
                frappe.bold(tender_item_name),
                ", ".join(existing),
            )
        )


def _clear_tender_item_link(
    tender_name,
    tender_item_name,
    cst_name,
):
    if not frappe.db.exists(
        "PEPL Tender",
        tender_name,
    ):
        return

    tender = frappe.get_doc(
        "PEPL Tender",
        tender_name,
    )

    tender_item = _get_tender_item(
        tender,
        tender_item_name,
    )

    if not tender_item:
        return

    if tender_item.linked_cost_sheet != cst_name:
        return

    tender_item.linked_cost_sheet = None
    tender_item.our_bid_unit_price = 0

    _set_tender_costing_status(tender)

    tender.flags.ignore_version = True
    tender.save(ignore_permissions=True)


def _refresh_tender_costing_status(tender_name):
    if not frappe.db.exists(
        "PEPL Tender",
        tender_name,
    ):
        return

    tender = frappe.get_doc(
        "PEPL Tender",
        tender_name,
    )

    _set_tender_costing_status(tender)

    tender.flags.ignore_version = True
    tender.save(ignore_permissions=True)


def _set_tender_costing_status(tender):
    if tender.status in TERMINAL_TENDER_STATUSES:
        return

    item_count = len(tender.items or [])

    if item_count == 0:
        return

    linked_count = 0

    for row in tender.items or []:
        if (
            row.linked_cost_sheet
            and frappe.db.exists(
                "PEPL CST Cost Sheet",
                row.linked_cost_sheet,
            )
        ):
            linked_count += 1

    if linked_count == item_count:
        tender.status = "Costed"
    elif linked_count > 0:
        tender.status = "Costing"
    elif tender.status in {
        "Costing",
        "Costed",
    }:
        tender.status = "Draft"
