"""List View hover preview: rest the mouse on a row of any List View to see a summary card of that record.

The browser side is public/js/pepl_list_hover.bundle.js (+ .bundle.css); it calls get_preview() below.
It lives in pepl_sales because pepl_sales is on every PEPL site; pepl_os DocTypes are covered too.

How a card is built
-------------------
* DocTypes in PREVIEW_CONFIG use the fields and child tables given there.
* Every other DocType gets an automatic card: its "In List View", "In Standard Filter" and "Bold" fields,
  then its first child tables (columns = the child's "In List View" fields).
* A submitted document also shows its GL Entries and Stock Movement, only to users who may read
  GL Entry / Stock Ledger Entry (so Stores and shop-floor users never see accounts).
* ERPNext permissions decide everything: no read right on the record means no card, and fields
  hidden by permission level or masked stay hidden.
"""

import frappe
from frappe import _
from frappe.model import no_value_fields, table_fields
from frappe.utils import cint, flt, strip_html

MAX_HEADER_FIELDS = 10
MAX_TABLES = 2
MAX_COLUMNS = 6
MAX_ROWS = 15
MAX_TEXT = 120

# DocTypes that never show a card.
EXCLUDED_DOCTYPES: set[str] = set()

# Never shown, even when listed in PREVIEW_CONFIG.
HARD_SKIP = (
	set(no_value_fields)
	| set(table_fields)
	| {
		"Password",
		"Attach",
		"Attach Image",
		"Signature",
		"Barcode",
		"Geolocation",
		"JSON",
		"Code",
		"HTML Editor",
	}
)

# Also left out of automatic cards (long text clutters the card).
AUTO_SKIP = HARD_SKIP | {"Text", "Small Text", "Long Text", "Text Editor", "Markdown Editor"}

NUMERIC = {"Currency", "Float", "Int", "Percent"}
SUMMABLE = {"Currency", "Float"}  # Int columns are ranks, days, counts per line: never totalled
NOT_SUMMED = ("rate", "price", "percent", "discount", "factor", "level", "consumption", "rank", "days")

HIGHLIGHT_CANDIDATES = ("grand_total", "total_amount", "paid_amount")

# Per-DocType layout. A field name that does not exist is skipped, so a renamed field never breaks a list.
#   fields    : header fields (the grey chips), in order; omit for the automatic choice
#   highlight : one amount shown large, e.g. Grand Total; omit to auto-pick, None for none
#   tables    : child tables in order; a plain string uses the child's "In List View" columns.
#               Per table: "columns" = field names, or (field name, label) to show a shorter label;
#               "totals" = None (automatic), False (no Total row) or the list of columns to total
#   ledgers   : False hides the GL Entries / Stock Movement sections
ITEMS = [("item_name", "Item"), ("qty", "Qty"), "rate", "amount"]

PREVIEW_CONFIG: dict[str, dict] = {
	# ---- ERPNext: Sales (Cycle 1)
	"Quotation": {
		"fields": ["party_name", "transaction_date", "status", "valid_till"],
		"tables": [{"fieldname": "items", "columns": ITEMS}],
	},
	"Sales Order": {
		"fields": ["customer", "transaction_date", "status", "delivery_date"],
		"tables": [{"fieldname": "items", "columns": ITEMS}],
	},
	"Delivery Note": {
		"fields": ["customer", "posting_date", "status", "lr_no"],
		"tables": [{"fieldname": "items", "columns": ITEMS}],
	},
	"Sales Invoice": {
		"fields": ["customer", "posting_date", "status", "due_date"],
		"tables": [{"fieldname": "items", "columns": ITEMS}],
	},
	# ---- ERPNext: Purchase & Stores (Cycle 2)
	"Material Request": {
		"fields": ["material_request_type", "transaction_date", "status", "schedule_date"],
		"tables": [
			{"fieldname": "items", "columns": [("item_name", "Item"), ("qty", "Qty"), "uom", "warehouse"]}
		],
	},
	"Purchase Order": {
		"fields": ["supplier", "transaction_date", "status", "schedule_date"],
		"tables": [{"fieldname": "items", "columns": ITEMS}],
	},
	"Purchase Receipt": {
		"fields": ["supplier", "posting_date", "status", "supplier_delivery_note"],
		"tables": [
			{
				"fieldname": "items",
				"columns": [
					("item_name", "Item"),
					("qty", "Qty"),
					("rejected_qty", "Rejected"),
					"rate",
					"amount",
				],
			}
		],
	},
	"Purchase Invoice": {
		"fields": ["supplier", "posting_date", "status", "due_date", "bill_no"],
		"tables": [{"fieldname": "items", "columns": ITEMS}],
	},
	"Stock Entry": {
		"fields": ["stock_entry_type", "posting_date", "work_order"],
		"tables": [
			{
				"fieldname": "items",
				"columns": [
					("item_code", "Item"),
					("qty", "Qty"),
					("s_warehouse", "From"),
					("t_warehouse", "To"),
				],
			}
		],
	},
	"Payment Entry": {
		"fields": ["payment_type", "party", "posting_date", "mode_of_payment", "reference_no", "status"],
		"highlight": "paid_amount",
		"tables": [
			{
				"fieldname": "references",
				"columns": [
					("reference_doctype", "Type"),
					("reference_name", "Document"),
					("allocated_amount", "Allocated"),
				],
			}
		],
	},
	# ---- ERPNext: Production (Work Order is PEPL's Job Order)
	"Work Order": {
		"fields": ["production_item", "qty", "produced_qty", "status", "planned_start_date", "sales_order"],
		"highlight": None,
		"tables": [
			{
				"fieldname": "required_items",
				"columns": [
					("item_code", "Item"),
					("required_qty", "Required"),
					("transferred_qty", "Transferred"),
					("consumed_qty", "Consumed"),
				],
				"totals": False,
			}
		],
	},
	# ---- pepl_os: totals only where adding the lines up means something
	"PEPL Payment Run": {"tables": [{"fieldname": "items", "totals": ["outstanding"]}]},
	"PEPL Quotation Comparison": {"tables": [{"fieldname": "rows", "totals": False}]},
	"PEPL Cycle Count": {"tables": [{"fieldname": "items", "totals": False}]},
	"PEPL Reorder Review": {"tables": [{"fieldname": "items", "totals": False}]},
	# ---- pepl_sales
	"PEPL CST Cost Sheet": {"tables": [{"fieldname": "components", "totals": False}]},
	"PEPL Tender": {
		"tables": [
			{"fieldname": "items", "totals": ["estimated_total_value"]},
			{"fieldname": "po_schedule", "totals": ["po_total"]},
		]
	},
	"PEPL Product Master": {
		"tables": [{"fieldname": "assembly_components", "totals": False}, "drawing_revisions"]
	},
}


@frappe.whitelist()
def get_preview(doctype: str, name: str) -> dict:
	"""The summary card for one record. Never raises for a missing record or a missing right."""
	if doctype in EXCLUDED_DOCTYPES:
		return {"hidden": 1}

	try:
		meta = frappe.get_meta(doctype)
	except frappe.DoesNotExistError:
		return {"hidden": 1}
	if meta.issingle or meta.istable:
		return {"hidden": 1}

	try:
		doc = frappe.get_doc(doctype, name)
	except frappe.DoesNotExistError:
		return {"missing": 1}

	if not doc.has_permission("read"):
		return {"denied": 1}
	doc.apply_fieldlevel_read_permissions()

	cfg = PREVIEW_CONFIG.get(doctype) or {}
	highlight = _highlight(doc, meta, cfg)
	skip = {meta.title_field, highlight["fieldname"] if highlight else None}

	return {
		"title": _title(doc, meta),
		"header": _header_fields(doc, meta, cfg.get("fields"), skip),
		"highlight": highlight,
		"tables": _child_tables(doc, meta, cfg.get("tables")),
		"ledgers": [] if cfg.get("ledgers") is False else _ledgers(doc),
	}


# ---------------------------------------------------------------------------------------------- helpers


def _fmt(value, df, doc=None, currency=None):
	if df.fieldtype == "Check":
		return _("Yes") if cint(value) else _("No")
	if value in (None, ""):
		return ""
	try:
		text = frappe.format_value(value, df, doc, currency=currency)
	except Exception:
		text = value
	text = strip_html(str(text if text is not None else "")).strip()
	if df.fieldtype == "Select":
		text = _(text)
	if len(text) > MAX_TEXT:
		text = text[: MAX_TEXT - 1] + "…"
	return text


def _title(doc, meta):
	if meta.title_field and doc.get(meta.title_field):
		return str(doc.get(meta.title_field))
	return doc.name


def _highlight(doc, meta, cfg):
	if "highlight" in cfg:
		fieldnames = [cfg["highlight"]] if cfg["highlight"] else []
	else:
		fieldnames = HIGHLIGHT_CANDIDATES
	for fieldname in fieldnames:
		df = meta.get_field(fieldname)
		if df and df.fieldtype in NUMERIC and doc.get(fieldname) is not None:
			return {"fieldname": fieldname, "label": _(df.label), "value": _fmt(doc.get(fieldname), df, doc)}
	return None


def _header_fields(doc, meta, wanted, skip):
	if wanted:
		dfs = [meta.get_field(f) for f in wanted]
		dfs = [df for df in dfs if df and df.fieldtype not in HARD_SKIP]
	else:
		dfs = [
			df
			for df in meta.fields
			if df.fieldtype not in AUTO_SKIP
			and not df.hidden
			and (df.in_list_view or df.in_standard_filter or df.bold or df.fieldname == "status")
		]

	out = []
	for df in dfs:
		if df.fieldname in skip:
			continue
		value = doc.get(df.fieldname)
		if value in (None, ""):
			continue
		# automatic cards leave out zero amounts and quantities
		if not wanted and df.fieldtype in NUMERIC and not flt(value):
			continue
		out.append(
			{"fieldname": df.fieldname, "label": _(df.label or df.fieldname), "value": _fmt(value, df, doc)}
		)
		if len(out) >= MAX_HEADER_FIELDS:
			break
	return out


def _child_tables(doc, meta, wanted):
	specs = []
	if wanted is not None:
		for spec in wanted:
			if isinstance(spec, str):
				spec = {"fieldname": spec}
			df = meta.get_field(spec.get("fieldname"))
			if df and df.fieldtype in table_fields:
				specs.append((df, spec))
	else:
		specs = [(df, {}) for df in meta.fields if df.fieldtype == "Table" and not df.hidden][:MAX_TABLES]

	result = []
	for df, spec in specs:
		rows = doc.get(df.fieldname) or []
		if rows:
			table = _table(df, rows, spec.get("columns"), spec.get("totals"))
			if table:
				result.append(table)
	return result


def _column_specs(columns):
	"""("fieldname", "Label") or "fieldname" -> [(fieldname, label or None)]."""
	out = []
	for column in columns:
		if isinstance(column, list | tuple):
			out.append((column[0], column[1]))
		else:
			out.append((column, None))
	return out


def _table(table_df, rows, columns=None, totals=None):
	child_meta = frappe.get_meta(table_df.options)

	if columns:
		cols = [(child_meta.get_field(f), label) for f, label in _column_specs(columns)]
		cols = [(c, label) for c, label in cols if c and c.fieldtype not in HARD_SKIP]
	else:
		usable = [c for c in child_meta.fields if c.fieldtype not in AUTO_SKIP and not c.hidden]
		cols = [(c, None) for c in ([c for c in usable if c.in_list_view][:MAX_COLUMNS] or usable[:4])]
	if not cols:
		return None
	col_dfs = [c for c, _label in cols]

	body = [[_fmt(row.get(c.fieldname), c, row) for c in col_dfs] for row in rows[:MAX_ROWS]]

	if totals is False:
		summed = [False] * len(col_dfs)
	elif totals:
		summed = [c.fieldname in totals and c.fieldtype in NUMERIC for c in col_dfs]
	else:
		summed = [
			c.fieldtype in SUMMABLE and not any(word in c.fieldname for word in NOT_SUMMED) for c in col_dfs
		]

	total_row = None
	if any(summed):
		total_row = [
			_fmt(sum(flt(r.get(c.fieldname)) for r in rows), c, rows[0]) if s else ""
			for c, s in zip(col_dfs, summed, strict=True)
		]
		if not total_row[0]:
			total_row[0] = _("Total")

	return {
		"label": _(table_df.label or table_df.fieldname),
		"columns": [
			{"label": _(label or c.label or c.fieldname), "numeric": c.fieldtype in NUMERIC}
			for c, label in cols
		],
		"rows": body,
		"totals": total_row,
		"more": max(0, len(rows) - MAX_ROWS),
	}


def _ledgers(doc):
	if doc.docstatus != 1:
		return []

	money_df = frappe._dict(fieldtype="Currency")
	qty_df = frappe._dict(fieldtype="Float")
	text_df = frappe._dict(fieldtype="Data")
	currency = (
		frappe.get_cached_value("Company", doc.company, "default_currency") if doc.get("company") else None
	)

	def money(value):
		return _fmt(flt(value), money_df, currency=currency)

	out = []

	if frappe.db.exists("DocType", "GL Entry") and frappe.has_permission("GL Entry", "read"):
		gl = frappe.db.sql(
			"""
			select account, sum(debit) as debit, sum(credit) as credit, remarks
			from `tabGL Entry`
			where voucher_type = %s and voucher_no = %s and is_cancelled = 0
			group by account, remarks
			order by min(creation)
			""",
			(doc.doctype, doc.name),
			as_dict=True,
		)
		if gl:
			# Remarks column only when a line has real remarks (ERPNext writes "No Remarks" otherwise)
			remarks = any(r.remarks and r.remarks.strip() not in ("No Remarks", _("No Remarks")) for r in gl)
			columns = [
				{"label": _("Account"), "numeric": False},
				{"label": _("Debit"), "numeric": True},
				{"label": _("Credit"), "numeric": True},
			]
			if remarks:
				columns.append({"label": _("Remarks"), "numeric": False})

			def gl_row(r):
				row = [r.account, money(r.debit), money(r.credit)]
				return [*row, _fmt(r.remarks or "", text_df)] if remarks else row

			totals = [_("Total"), money(sum(flt(r.debit) for r in gl)), money(sum(flt(r.credit) for r in gl))]
			out.append(
				{
					"label": _("GL Entries"),
					"columns": columns,
					"rows": [gl_row(r) for r in gl[:MAX_ROWS]],
					"totals": [*totals, ""] if remarks else totals,
					"more": max(0, len(gl) - MAX_ROWS),
				}
			)

	if frappe.db.exists("DocType", "Stock Ledger Entry") and frappe.has_permission(
		"Stock Ledger Entry", "read"
	):
		sle = frappe.db.sql(
			"""
			select item_code, warehouse, sum(actual_qty) as qty, sum(stock_value_difference) as value
			from `tabStock Ledger Entry`
			where voucher_type = %s and voucher_no = %s and is_cancelled = 0
			group by item_code, warehouse
			order by min(creation)
			""",
			(doc.doctype, doc.name),
			as_dict=True,
		)
		if sle:
			out.append(
				{
					"label": _("Stock Movement"),
					"columns": [
						{"label": _("Item"), "numeric": False},
						{"label": _("Warehouse"), "numeric": False},
						{"label": _("Qty In / Out"), "numeric": True},
						{"label": _("Value Change"), "numeric": True},
					],
					"rows": [
						[r.item_code, r.warehouse, _fmt(flt(r.qty), qty_df), money(r.value)]
						for r in sle[:MAX_ROWS]
					],
					"totals": None,
					"more": max(0, len(sle) - MAX_ROWS),
				}
			)

	return out
