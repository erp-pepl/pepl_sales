frappe.ui.form.on("PEPL Product Master", {
	refresh(frm) {
		const status_colors = {
			"Active": "green",
			"Under Development": "yellow",
			"Obsolete": "red"
		};
		if (frm.doc.status) {
			frm.page.set_indicator(frm.doc.status, status_colors[frm.doc.status]);
		}

		if (!frm.is_new()) {
			// Sync from BOM (only for assemblies)
			if (frm.doc.product_type === "Assembly" || frm.doc.product_type === "Sub-Assembly") {
				frm.add_custom_button(__("Sync Components from BOM"), function() {
					if (!frm.doc.linked_bom) {
						frappe.msgprint(__("Set Linked BOM first"));
						return;
					}
					frappe.confirm(
						__("This will replace all existing assembly components. Continue?"),
						function() {
							frappe.call({
								method: "pepl_sales.pepl_sales.doctype.pepl_product_master.pepl_product_master.sync_components_from_bom",
								args: { product_name: frm.doc.name },
								callback: function(r) {
									if (r.message) {
										frappe.show_alert({
											message: __("Synced {0} components from BOM", [r.message.synced]),
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

			// Add New Drawing Revision
			frm.add_custom_button(__("Add New Drawing Revision"), function() {
				const new_row = frm.add_child("drawing_revisions");
				new_row.is_current = 1;
				new_row.issue_date = frappe.datetime.get_today();

				(frm.doc.drawing_revisions || []).forEach(r => {
					if (r.name !== new_row.name) {
						r.is_current = 0;
					}
				});

				frm.refresh_field("drawing_revisions");
				frappe.show_alert({
					message: __("New revision row added — attach file and update revision letter"),
					indicator: "blue"
				});
			}, __("Actions"));
		}
	},

	primary_customer(frm) {
		if (frm.doc.primary_customer && !frm.doc.sub_sector) {
			frappe.db.get_value("Customer", frm.doc.primary_customer, "customer_group", (r) => {
				if (r && r.customer_group) {
					frm.set_value("sub_sector", r.customer_group);
					if (r.customer_group.includes("Railways")) {
						frm.set_value("sector", "Railways");
					} else if (r.customer_group.includes("Defence")) {
						frm.set_value("sector", "Defence");
					}
				}
			});
		}
	}
});

frappe.ui.form.on("PEPL Product Drawing Revision", {
	is_current(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.is_current) {
			(frm.doc.drawing_revisions || []).forEach(r => {
				if (r.name !== cdn) {
					frappe.model.set_value(r.doctype, r.name, "is_current", 0);
				}
			});
		}
	}
});
