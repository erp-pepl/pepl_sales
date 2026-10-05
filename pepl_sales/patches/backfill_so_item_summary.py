import frappe
from pepl_sales.pepl_sales.overrides.sales_order import build_item_summary


def execute():
    for name in frappe.get_all("Sales Order", pluck="name"):
        doc = frappe.get_doc("Sales Order", name)
        frappe.db.set_value(
            "Sales Order", name, "custom_item_summary",
            build_item_summary(doc), update_modified=False,
        )