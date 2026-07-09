frappe.ui.form.on("PEPL Company Document", {
	refresh(frm) {
		if (frm.doc.current_expiry_date) {
			const expiry = frappe.datetime.str_to_obj(frm.doc.current_expiry_date);
			const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
			const days_to_expiry = Math.floor((expiry - today) / (1000 * 60 * 60 * 24));

			if (days_to_expiry < 0) {
				frm.page.set_indicator("Expired", "red");
			} else if (days_to_expiry < 30) {
				frm.page.set_indicator(`Expires in ${days_to_expiry} days`, "orange");
			} else if (days_to_expiry < 90) {
				frm.page.set_indicator(`Expires in ${days_to_expiry} days`, "yellow");
			} else {
				frm.page.set_indicator("Active", "green");
			}
		} else if (frm.doc.is_active) {
			frm.page.set_indicator("Active (no expiry)", "green");
		} else {
			frm.page.set_indicator("Inactive", "grey");
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__("Add New Version (Renewal)"), function() {
				const new_row = frm.add_child("versions");
				new_row.is_current = 1;
				new_row.issue_date = frappe.datetime.get_today();

				(frm.doc.versions || []).forEach(v => {
					if (v.name !== new_row.name) {
						v.is_current = 0;
					}
				});

				frm.refresh_field("versions");
				frappe.show_alert({
					message: __("New version row added — please attach the renewed document file"),
					indicator: "blue"
				});

				setTimeout(() => {
					const grid = frm.fields_dict.versions.grid;
					grid.scroll_to_row(grid.grid_rows.length - 1);
				}, 200);
			}, __("Actions"));
		}
	},

	document_type(frm) {
		const category_map = {
			"Udyam Aadhaar": "Statutory",
			"MSME Certificate (SSI)": "Statutory",
			"GST Certificate": "Statutory",
			"PAN Card": "Statutory",
			"Incorporation Certificate": "Company Records",
			"Factory License": "Statutory",
			"Trade License": "Statutory",
			"Electricity Certificate / Connection": "Company Records",
			"Rent Agreement / Lease Deed": "Company Records",
			"Pollution Certificate (CTE/CTO)": "Statutory",
			"Centralised Vendor Registration Certificate": "Company Records",
			"Bank Statement": "Financial",
			"Plant and Machinery List": "Company Records",
			"Instruments and Testing Facilities List": "Company Records",
			"ISO 9001:2015 Certificate": "Quality Certification",
			"ISO 14001 Certificate": "Quality Certification",
			"ISO 45001 Certificate": "Quality Certification",
			"AS9100D Certificate": "Quality Certification",
			"IATF 16949 Certificate": "Quality Certification",
			"IRIS Certificate": "Quality Certification",
			"Income Tax Return Acknowledgement": "Financial",
			"Balance Sheet": "Financial",
			"Audited Financials": "Financial"
		};

		if (frm.doc.document_type && category_map[frm.doc.document_type] && !frm.doc.category) {
			frm.set_value("category", category_map[frm.doc.document_type]);
		}
	}
});

frappe.ui.form.on("PEPL Company Document Version", {
	is_current(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.is_current) {
			(frm.doc.versions || []).forEach(v => {
				if (v.name !== cdn) {
					frappe.model.set_value(v.doctype, v.name, "is_current", 0);
				}
			});
		}
	}
});
