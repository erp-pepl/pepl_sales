"""List View hover preview: the card returned by pepl_sales.list_preview.get_preview."""

import frappe
from frappe.model import table_fields
from frappe.tests.utils import FrappeTestCase

from pepl_sales import list_preview as lp
from pepl_sales.setup import sales_order_list as sol

RM_GROUP = "PEPL T LP Brass"


def _unsaved_sales_order():
	"""Two item lines, 1 x 2,423 and 24 x 23,423 (not saved, so no masters are needed)."""
	return frappe.get_doc(
		{
			"doctype": "Sales Order",
			"items": [
				{"item_name": "CSM Aluminium Scrap", "qty": 1, "rate": 2423, "amount": 2423},
				{"item_name": "CSM Brass Solid", "qty": 24, "rate": 23423, "amount": 562152},
			],
		}
	)


class TestListPreview(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("PEPL RM Group", RM_GROUP):
			frappe.get_doc(
				{"doctype": "PEPL RM Group", "group_name": RM_GROUP, "material_base": "Brass"}
			).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_automatic_card_for_a_doctype_not_configured(self):
		self.assertNotIn("PEPL RM Group", lp.PREVIEW_CONFIG)
		card = lp.get_preview("PEPL RM Group", RM_GROUP)
		fields = {f["fieldname"]: f["value"] for f in card["header"]}
		self.assertEqual(fields.get("material_base"), "Brass")
		self.assertEqual(card["ledgers"], [])  # not a submitted accounting document

	def test_no_card_without_read_right(self):
		frappe.set_user("Guest")
		self.assertEqual(lp.get_preview("PEPL RM Group", RM_GROUP), {"denied": 1})

	def test_missing_record_child_table_and_unknown_doctype(self):
		self.assertEqual(lp.get_preview("PEPL RM Group", "PEPL T LP No Such Group"), {"missing": 1})
		self.assertEqual(lp.get_preview("Sales Order Item", "anything"), {"hidden": 1})
		self.assertEqual(lp.get_preview("PEPL No Such DocType", "anything"), {"hidden": 1})

	def test_excluded_doctype(self):
		lp.EXCLUDED_DOCTYPES.add("PEPL RM Group")
		try:
			self.assertEqual(lp.get_preview("PEPL RM Group", RM_GROUP), {"hidden": 1})
		finally:
			lp.EXCLUDED_DOCTYPES.discard("PEPL RM Group")

	def test_sales_order_items_table_short_labels_and_total(self):
		so = _unsaved_sales_order()
		[table] = lp._child_tables(
			so, frappe.get_meta("Sales Order"), lp.PREVIEW_CONFIG["Sales Order"]["tables"]
		)
		self.assertEqual([c["label"] for c in table["columns"]][:2], ["Item", "Qty"])
		self.assertEqual(len(table["rows"]), 2)

		child = frappe.get_meta("Sales Order Item")
		qty, rate, amount = table["totals"][1:]
		self.assertEqual(qty, lp._fmt(25.0, child.get_field("qty"), so.items[0]))
		self.assertEqual(rate, "")  # rates are never added up
		self.assertEqual(amount, lp._fmt(564575.0, child.get_field("amount"), so.items[0]))

	def test_total_row_switched_off_or_limited(self):
		so = _unsaved_sales_order()
		meta = frappe.get_meta("Sales Order")
		[table] = lp._child_tables(so, meta, [{"fieldname": "items", "totals": False}])
		self.assertIsNone(table["totals"])
		[table] = lp._child_tables(
			so, meta, [{"fieldname": "items", "columns": lp.ITEMS, "totals": ["amount"]}]
		)
		self.assertEqual(table["totals"][1], "")  # qty not totalled this time
		self.assertTrue(table["totals"][3])

	def test_frappe_own_preview_removed_from_sales_order(self):
		"""Regression: Frappe's own popup was switched on for Sales Order, giving two cards on hover."""
		frappe.get_doc(
			{
				"doctype": "Property Setter",
				"doctype_or_field": "DocType",
				"doc_type": "Sales Order",
				"property": "show_preview_popup",
				"property_type": "Check",
				"value": "1",
			}
		).insert(ignore_permissions=True)
		sol._remove_old_preview_settings()
		self.assertFalse(
			frappe.db.exists("Property Setter", {"doc_type": "Sales Order", "property": "show_preview_popup"})
		)

	def test_every_configured_field_exists(self):
		"""A field renamed in ERPNext, pepl_sales or pepl_os would quietly vanish from the card; catch it here."""
		for doctype, cfg in lp.PREVIEW_CONFIG.items():
			if not frappe.db.exists("DocType", doctype):
				continue  # a pepl_os DocType on a site without pepl_os
			meta = frappe.get_meta(doctype)
			for fieldname in cfg.get("fields") or []:
				self.assertTrue(meta.get_field(fieldname), f"{doctype}.{fieldname}")
			if cfg.get("highlight"):
				self.assertTrue(meta.get_field(cfg["highlight"]), f"{doctype}.{cfg['highlight']}")
			for spec in cfg.get("tables") or []:
				spec = {"fieldname": spec} if isinstance(spec, str) else spec
				df = meta.get_field(spec["fieldname"])
				self.assertTrue(df and df.fieldtype in table_fields, f"{doctype}.{spec['fieldname']}")
				child = frappe.get_meta(df.options)
				columns = [f for f, _label in lp._column_specs(spec.get("columns") or [])]
				for column in columns + list(spec.get("totals") or []):
					self.assertTrue(child.get_field(column), f"{doctype}.{spec['fieldname']}.{column}")
