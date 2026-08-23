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
    Show an operational advisory for incomplete PEPL customer documents.

    Pending customer documents remain visible in PEPL Document Tracker,
    but they must not prevent Sales Invoice submission.
    """

    sales_orders = _get_linked_sales_orders(
        doc
    )

    # Sales Invoice may legitimately exist without a Sales Order.
    if not sales_orders:
        return

    pending_groups = []

    for sales_order in sales_orders:
        tracker_names = frappe.get_all(
            "PEPL Document Tracker",
            filters={
                "linked_sales_order":
                    sales_order,
            },
            pluck="name",
        )

        if not tracker_names:
            pending_groups.append(
                {
                    "sales_order":
                        sales_order,
                    "tracker":
                        None,
                    "documents": [
                        _(
                            "Document Tracker not found"
                        )
                    ],
                }
            )
            continue

        for tracker_name in tracker_names:
            rows = frappe.get_all(
                "PEPL Document Entry",
                filters={
                    "parent":
                        tracker_name,
                    "parenttype":
                        "PEPL Document Tracker",
                    "parentfield":
                        "document_entries",
                    "is_required":
                        1,
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
                status = (
                    row.document_status
                    or ""
                )

                if (
                    status
                    not in COMPLETED_DOCUMENT_STATUSES
                ):
                    incomplete_documents.append(
                        "{} ({})".format(
                            (
                                row.document_type
                                or _(
                                    "Unnamed Document"
                                )
                            ),
                            (
                                status
                                or _("Not Set")
                            ),
                        )
                    )

            if incomplete_documents:
                pending_groups.append(
                    {
                        "sales_order":
                            sales_order,
                        "tracker":
                            tracker_name,
                        "documents":
                            incomplete_documents,
                    }
                )

    if not pending_groups:
        return

    detail_blocks = []

    for group in pending_groups:
        sales_order_link = (
            get_link_to_form(
                "Sales Order",
                group["sales_order"],
            )
        )

        tracker_link = (
            get_link_to_form(
                "PEPL Document Tracker",
                group["tracker"],
            )
            if group["tracker"]
            else _("Not Found")
        )

        detail_blocks.append(
            _(
                "<b>Sales Order:</b> {0}<br>"
                "<b>Document Tracker:</b> {1}<br>"
                "<b>Pending Required Documents:</b> {2}"
            ).format(
                sales_order_link,
                tracker_link,
                ", ".join(
                    group["documents"]
                ),
            )
        )

    frappe.msgprint(
        _(
            "Sales Invoice submission will continue. "
            "The following customer documents are still "
            "pending and must continue to be followed up."
            "<br><br>{0}"
        ).format(
            "<br><br>".join(
                detail_blocks
            )
        ),
        title=_(
            "Required Documents Pending — Advisory"
        ),
        indicator="orange",
    )


def _get_linked_sales_orders(doc: Document) -> list[str]:
    """Return distinct Sales Orders referenced by invoice items."""

    sales_orders = set()

    for item in doc.get("items") or []:
        sales_order = item.get("sales_order")

        if sales_order:
            sales_orders.add(sales_order)

    return sorted(sales_orders)
