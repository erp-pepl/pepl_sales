from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


COMPLETED_DOCUMENT_STATUSES = {
    "Received",
    "Filed",
}


def validate_document_readiness_before_submit(
    doc: Document,
    method: str | None = None,
) -> None:
    """
    Prevent Sales Invoice submission until all required
    PEPL Document Tracker entries for every linked Sales Order
    are complete.

    Draft Sales Invoices remain allowed.
    """

    sales_orders = _get_linked_sales_orders(doc)

    # Invoice may legitimately exist without a Sales Order.
    # PEPL document gating only applies where a Sales Order
    # is explicitly referenced in Sales Invoice Item.
    if not sales_orders:
        return

    blockers = []

    for sales_order in sales_orders:
        tracker_names = frappe.get_all(
            "PEPL Document Tracker",
            filters={
                "linked_sales_order": sales_order,
            },
            pluck="name",
        )

        # Missing tracker is itself a blocking condition.
        if not tracker_names:
            blockers.append(
                {
                    "sales_order": sales_order,
                    "tracker": None,
                    "documents": [
                        _("Document Tracker not found")
                    ],
                }
            )
            continue

        # PEPL design expects one Document Tracker per Sales Order.
        # Multiple trackers are treated conservatively:
        # every tracker is inspected.
        for tracker_name in tracker_names:
            rows = frappe.get_all(
                "PEPL Document Entry",
                filters={
                    "parent": tracker_name,
                    "parenttype": "PEPL Document Tracker",
                    "parentfield": "document_entries",
                    "is_required": 1,
                },
                fields=[
                    "document_type",
                    "document_status",
                    "idx",
                ],
                order_by="idx asc",
            )

            incomplete_documents = []

            for row in rows:
                status = row.document_status or ""

                if status not in COMPLETED_DOCUMENT_STATUSES:
                    incomplete_documents.append(
                        "{} ({})".format(
                            row.document_type or _("Unnamed Document"),
                            status or _("Not Set"),
                        )
                    )

            if incomplete_documents:
                blockers.append(
                    {
                        "sales_order": sales_order,
                        "tracker": tracker_name,
                        "documents": incomplete_documents,
                    }
                )

    if not blockers:
        return

    detail_blocks = []

    for blocker in blockers:
        sales_order_link = get_link_to_form(
            "Sales Order",
            blocker["sales_order"],
        )

        tracker_link = (
            get_link_to_form(
                "PEPL Document Tracker",
                blocker["tracker"],
            )
            if blocker["tracker"]
            else _("Not Found")
        )

        detail_blocks.append(
            _(
                "<b>Sales Order:</b> {0}<br>"
                "<b>Document Tracker:</b> {1}<br>"
                "<b>Incomplete Required Documents:</b> {2}"
            ).format(
                sales_order_link,
                tracker_link,
                ", ".join(blocker["documents"]),
            )
        )

    frappe.throw(
        _(
            "Sales Invoice cannot be submitted because required "
            "customer documents are incomplete.<br><br>{0}"
        ).format(
            "<br><br>".join(detail_blocks)
        ),
        title=_("Required Documents Pending"),
    )


def _get_linked_sales_orders(doc: Document) -> list[str]:
    """Return distinct Sales Orders referenced by invoice items."""

    sales_orders = set()

    for item in doc.get("items") or []:
        sales_order = item.get("sales_order")

        if sales_order:
            sales_orders.add(sales_order)

    return sorted(sales_orders)
