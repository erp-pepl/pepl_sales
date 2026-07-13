import frappe
from frappe.custom.doctype.custom_field.custom_field import (
    create_custom_fields,
)


def execute():
    """
    Create the ERPNext custom fields required by PEPL Sales Cycle 1.

    The operation is idempotent and safe to run repeatedly.
    """

    custom_fields = {
        "Sales Order": [
            {
                "fieldname": "custom_tender_reference",
                "label": "PEPL Tender Reference",
                "fieldtype": "Link",
                "options": "PEPL Tender",
                "insert_after": "po_date",
                "read_only": 1,
                "no_copy": 1,
                "in_standard_filter": 1,
                "description": (
                    "PEPL Tender from which this Sales Order originated."
                ),
            },
            {
                "fieldname": "custom_nit_number",
                "label": "NIT Number / Tender Reference",
                "fieldtype": "Data",
                "insert_after": "custom_tender_reference",
                "read_only": 1,
                "no_copy": 1,
                "in_standard_filter": 1,
            },
            {
                "fieldname": "custom_sector",
                "label": "PEPL Sector",
                "fieldtype": "Select",
                "options": "\nRailways\nDefence\nPrivate\nOthers",
                "insert_after": "custom_nit_number",
                "read_only": 1,
                "no_copy": 1,
                "in_standard_filter": 1,
            },
        ],
        "Item": [
            {
                "fieldname": "custom_pl_no",
                "label": "PL Number",
                "fieldtype": "Data",
                "insert_after": "item_name",
                "in_standard_filter": 1,
                "description": (
                    "Railway PL number managed by PEPL Sales."
                ),
            },
            {
                "fieldname": "custom_drawing_no",
                "label": "Drawing Number",
                "fieldtype": "Data",
                "insert_after": "custom_pl_no",
                "in_standard_filter": 1,
                "description": (
                    "Current PEPL drawing number for the Item."
                ),
            },
            {
                "fieldname": "custom_sector",
                "label": "PEPL Sector",
                "fieldtype": "Select",
                "options": "\nRailways\nDefence\nPrivate\nOthers",
                "insert_after": "custom_drawing_no",
                "in_standard_filter": 1,
            },
        ],
    }

    create_custom_fields(
        custom_fields,
        update=True,
    )

    frappe.clear_cache(
        doctype="Sales Order"
    )
    frappe.clear_cache(
        doctype="Item"
    )
