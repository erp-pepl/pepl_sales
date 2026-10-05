import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from pepl_sales.overrides.sales_order import build_item_summary

DOCTYPE = "Sales Order"
FIELDNAME = "custom_item_summary"


def setup_sales_order_list_view():
	"""Runs on after_install and after_migrate. Safe to run any number of times."""
	_create_item_summary_field()
	frappe.clear_cache(doctype=DOCTYPE)

	_set_doctype_property("title_field", FIELDNAME)
	_set_doctype_property("search_fields", _search_fields_with_summary())
	make_property_setter(
		DOCTYPE, "customer_name", "in_list_view", 1, "Check",
		validate_fields_for_doctype=False,
	)

	frappe.clear_cache(doctype=DOCTYPE)
	_backfill_item_summary()
	frappe.db.commit()


def _create_item_summary_field():
	create_custom_fields(
		{
			DOCTYPE: [
				{
					"fieldname": FIELDNAME,
					"label": "Item Summary",
					"fieldtype": "Data",
					"insert_after": "customer_name",
					"read_only": 1,
					"no_copy": 1,
					"allow_on_submit": 1,
					"in_standard_filter": 1,
					"translatable": 0,
				}
			]
		},
		update=True,
	)


def _set_doctype_property(prop, value):
	make_property_setter(
		DOCTYPE, None, prop, value, "Data",
		for_doctype=True, validate_fields_for_doctype=False,
	)


def _search_fields_with_summary():
	current = frappe.get_meta(DOCTYPE).search_fields or ""
	fields = [f.strip() for f in current.split(",") if f.strip()]
	if FIELDNAME not in fields:
		fields.append(FIELDNAME)
	return ",".join(fields)


def _backfill_item_summary():
	names = frappe.get_all(
		DOCTYPE,
		filters={FIELDNAME: ("is", "not set"), "docstatus": ("<", 2)},
		pluck="name",
	)
	for name in names:
		summary = build_item_summary(frappe.get_doc(DOCTYPE, name))
		if summary:
			frappe.db.set_value(DOCTYPE, name, FIELDNAME, summary, update_modified=False)