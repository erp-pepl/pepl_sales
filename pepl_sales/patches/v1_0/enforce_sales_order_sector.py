import frappe
from frappe.custom.doctype.custom_field.custom_field import (
    create_custom_fields,
)


def execute():
    """
    Backfill any remaining blank Sales Order sectors and enforce the
    mandatory, editable field definition.

    The patch is safe to run repeatedly.
    """

    blank_sales_orders = frappe.get_all(
        "Sales Order",
        filters={
            "custom_sector": ["in", ["", None]],
        },
        pluck="name",
        limit_page_length=0,
    )

    for sales_order_name in blank_sales_orders:
        frappe.db.set_value(
            "Sales Order",
            sales_order_name,
            "custom_sector",
            "Others",
            update_modified=False,
        )

    create_custom_fields(
        {
            "Sales Order": [
                {
                    "fieldname": "custom_sector",
                    "label": "PEPL Sector",
                    "fieldtype": "Select",
                    "options": (
                        "\nRailways\nDefence\nPrivate\nOthers"
                    ),
                    "insert_after": "custom_nit_number",
                    "reqd": 1,
                    "read_only": 0,
                    "no_copy": 1,
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

    frappe.clear_cache(doctype="Sales Order")
