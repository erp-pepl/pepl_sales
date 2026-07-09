frappe.ui.form.on("PEPL CST Cost Sheet", {
	refresh(frm) {
		const status_colors = {
			"Draft": "grey",
			"Under Review": "yellow",
			"Approved": "green",
			"Used in Bid": "blue",
			"Superseded": "orange",
			"Obsolete": "red"
		};
		if (frm.doc.status) {
			frm.page.set_indicator(frm.doc.status, status_colors[frm.doc.status]);
		}

		if (!frm.is_new() && frm.doc.linked_product) {
			frm.add_custom_button(__("Sync Components from Product"), function() {
				frappe.confirm(
					__("Replace existing components with those from Product Master?"),
					function() {
						frappe.call({
							method: "pepl_sales.pepl_sales.doctype.pepl_cst_cost_sheet.pepl_cst_cost_sheet.sync_components_from_product",
							args: { cst_name: frm.doc.name },
							callback: function(r) {
								if (r.message) {
									frappe.show_alert({
										message: __("Synced {0} components", [r.message.synced]),
										indicator: "green"
									});
									frm.reload_doc();
								}
							}
						});
					}
				);
			}, __("Actions"));
		}

		if (!frm.is_new() && frm.doc.linked_item) {
			frm.add_custom_button(__("Fetch Competitor History"), function() {
				frappe.call({
					method: "pepl_sales.pepl_sales.doctype.pepl_cst_cost_sheet.pepl_cst_cost_sheet.fetch_competitor_history",
					args: { cst_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({
								message: __("Loaded {0} competitor records from past tenders", [r.message.added]),
								indicator: "green"
							});
							frm.reload_doc();
						}
					}
				});
			}, __("Actions"));
		}

	},

	final_bid_price(frm) {
		if (frm.doc.suggested_unit_price && frm.doc.final_bid_price) {
			const diff = frm.doc.final_bid_price - frm.doc.suggested_unit_price;
			const indicator = diff < 0 ? "red" : (diff === 0 ? "blue" : "green");
			const msg = diff < 0
				? `\u20b9${Math.abs(diff).toFixed(2)} below suggested price`
				: (diff === 0 ? "Matching suggested price" : `\u20b9${diff.toFixed(2)} above suggested price`);
			frappe.show_alert({ message: msg, indicator: indicator });
		}
	}
});

frappe.ui.form.on("PEPL CST Component", {
	raw_material_cost: function(frm, cdt, cdn) { calculate_subtotal(frm, cdt, cdn); },
	machining_cost: function(frm, cdt, cdn) { calculate_subtotal(frm, cdt, cdn); },
	surface_treatment_cost: function(frm, cdt, cdn) { calculate_subtotal(frm, cdt, cdn); },
	bought_out_cost: function(frm, cdt, cdn) { calculate_subtotal(frm, cdt, cdn); },
	component_other_charges: function(frm, cdt, cdn) { calculate_subtotal(frm, cdt, cdn); },
	manufactured_or_bought_out: function(frm, cdt, cdn) { calculate_subtotal(frm, cdt, cdn); }
});

function calculate_subtotal(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	let subtotal = 0;

	if (row.manufactured_or_bought_out === "Manufactured") {
		subtotal = (row.raw_material_cost || 0)
			+ (row.machining_cost || 0)
			+ (row.surface_treatment_cost || 0)
			+ (row.component_other_charges || 0);
	} else {
		subtotal = (row.bought_out_cost || 0)
			+ (row.surface_treatment_cost || 0)
			+ (row.component_other_charges || 0);
	}

	frappe.model.set_value(cdt, cdn, "component_subtotal", subtotal);
}
