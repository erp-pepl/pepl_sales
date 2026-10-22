import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from pepl_sales.overrides.sales_order import build_item_summary

DOCTYPE = "Sales Order"
FIELDNAME = "custom_item_summary"

# Frappe's own preview popup was switched on here before; the PEPL hover card (pepl_sales/list_preview.py)
# replaces it on every list, so those settings are removed again to keep one card only.
OLD_PREVIEW_FIELDS = ("customer_name", "delivery_date", "grand_total", "status")


def setup_sales_order_list_view():
	"""Runs on after_install and after_migrate. Safe to run any number of times."""
	_create_item_summary_field()
	frappe.clear_cache(doctype=DOCTYPE)

	# List view: item summary as title, customer as a column, searchable by item
	_set_doctype_property("title_field", FIELDNAME, "Data")
	_set_doctype_property("search_fields", _search_fields_with_summary(), "Data")
	_set_field_property("customer_name", "in_list_view", 1)

	# One hover card only: the PEPL card. Remove Frappe's own preview settings made earlier.
	_remove_old_preview_settings()

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
					"in_preview": 0,
					"translatable": 0,
				}
			]
		},
		update=True,
	)


def _set_doctype_property(prop, value, prop_type):
	make_property_setter(
		DOCTYPE, None, prop, value, prop_type,
		for_doctype=True, validate_fields_for_doctype=False,
	)


def _set_field_property(fieldname, prop, value):
	make_property_setter(
		DOCTYPE, fieldname, prop, value, "Check",
		validate_fields_for_doctype=False,
	)


def _remove_old_preview_settings():
	"""Deleted, not set to 0: Frappe treats a 0 setter on a DocType without a built-in preview as 'on'."""
	frappe.db.delete("Property Setter", {"doc_type": DOCTYPE, "property": "show_preview_popup"})
	frappe.db.delete(
		"Property Setter",
		{"doc_type": DOCTYPE, "property": "in_preview", "field_name": ("in", OLD_PREVIEW_FIELDS)},
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