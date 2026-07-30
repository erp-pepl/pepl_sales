import frappe
from frappe.custom.doctype.custom_field.custom_field import (
    create_custom_fields,
)


VALID_SECTORS = {
    "Railways",
    "Defence",
    "Private",
    "Others",
}


def execute():
    """
    Create/update the mandatory PEPL Sector field and safely backfill
    historical Sales Orders.

    Existing valid values are preserved. Blank or invalid values are
    inferred from Customer Group where possible and otherwise set to Others.

    This patch is idempotent.
    """

    create_custom_fields(
        {
            "Sales Order": [
                {
                    "fieldname": "custom_sector",
                    "label": "PEPL Sector",
                    "fieldtype": "Select",
                    "options": "\nRailways\nDefence\nPrivate\nOthers",
                    "insert_after": "custom_nit_number",
                    "reqd": 1,
                    "read_only": 0,
                    "no_copy": 1,
                    "in_list_view": 1,
                    "in_standard_filter": 1,
                    "description": (
                        "Mandatory business sector used for "
                        "PEPL tracker generation."
                    ),
                },
            ],
        },
        update=True,
    )

    sales_orders = frappe.get_all(
        "Sales Order",
        fields=[
            "name",
            "customer",
            "custom_sector",
        ],
        limit_page_length=0,
    )

    updated = 0
    inferred = 0
    defaulted = 0

    for sales_order in sales_orders:
        current_sector = (
            sales_order.custom_sector or ""
        ).strip()

        if current_sector in VALID_SECTORS:
            continue

        sector = _infer_sector_from_customer(
            sales_order.customer
        )

        if sector == "Others":
            defaulted += 1
        else:
            inferred += 1

        frappe.db.set_value(
            "Sales Order",
            sales_order.name,
            "custom_sector",
            sector,
            update_modified=False,
        )

        updated += 1

    frappe.clear_cache(doctype="Sales Order")

    frappe.logger("pepl_sales").info(
        {
            "event": "sales_order_sector_backfill",
            "updated": updated,
            "inferred": inferred,
            "defaulted_to_others": defaulted,
        }
    )


def _infer_sector_from_customer(customer):
    if not customer:
        return "Others"

    customer_group = (
        frappe.db.get_value(
            "Customer",
            customer,
            "customer_group",
        )
        or ""
    ).strip().lower()

    if "railway" in customer_group:
        return "Railways"

    if "defence" in customer_group or "defense" in customer_group:
        return "Defence"

    if "private" in customer_group:
        return "Private"

    return "Others"
