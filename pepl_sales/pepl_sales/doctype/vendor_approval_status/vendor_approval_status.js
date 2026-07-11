frappe.ui.form.on("Vendor Approval Status", {
	refresh(frm) {
		if (frm.doc.sector === "Railways" && frm.doc.railways_stage) {
			const colors = {
				"Unapproved": "red",
				"Developmental": "orange",
				"Approved": "green"
			};
			frm.page.set_indicator(frm.doc.railways_stage, colors[frm.doc.railways_stage]);
		} else if (frm.doc.sector === "Defence" && frm.doc.defence_stage) {
			const colors = {
				"Source Development": "orange",
				"Approved / Established": "green"
			};
			frm.page.set_indicator(frm.doc.defence_stage, colors[frm.doc.defence_stage]);
		}

		if (frm.doc.sector && (frm.doc.railways_stage || frm.doc.defence_stage)) {
			frm.add_custom_button(__("Show Required Documents"), function() {
				frappe.call({
					method: "pepl_sales.pepl_sales.doctype.vendor_approval_status.vendor_approval_status.get_required_documents",
					args: {
						sector: frm.doc.sector,
						stage: frm.doc.sector === "Railways" ? frm.doc.railways_stage : frm.doc.defence_stage
					},
					callback: function(r) {
						if (r.message && r.message.length > 0) {
							const docs_list = r.message.map(d => `<li>${d}</li>`).join("");
							frappe.msgprint({
								title: __("Required Documents for This Stage"),
								message: `<ul>${docs_list}</ul>`,
								indicator: "blue"
							});
						}
					}
				});
			});
		}

		if (!frm.is_new() && frm.doc.sector) {
			frm.add_custom_button(__("Auto-Add Company Documents"), function() {
				const standard_docs = [
					"Udyam Aadhaar",
					"GST Certificate",
					"PAN Card"
				];

				let added = 0;
				standard_docs.forEach(doc_type => {
					const exists = (frm.doc.vendor_approval_documents || []).some(
						d => d.linked_company_document === doc_type || d.document_type === doc_type
					);
					if (!exists) {
						const new_row = frm.add_child("vendor_approval_documents");
						new_row.document_source = "Company Library";
						new_row.linked_company_document = doc_type;
						new_row.document_type = doc_type;
						added++;
					}
				});

				frm.refresh_field("vendor_approval_documents");
				frappe.show_alert({
					message: __("Added {0} standard company documents", [added]),
					indicator: "green"
				});
			}, __("Documents"));
		}
	},

	sector(frm) {
		if (frm.doc.sector === "Railways") {
			frm.set_value("defence_stage", "");
		} else if (frm.doc.sector === "Defence") {
			frm.set_value("railways_stage", "");
		}
	}
});

frappe.ui.form.on("Vendor Approval Document", {
	document_source(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.document_source === "Company Library") {
			frappe.model.set_value(cdt, cdn, "linked_drawing_revision", "");
			frappe.model.set_value(cdt, cdn, "linked_specification", "");
		} else if (row.document_source === "Item Drawing") {
			frappe.model.set_value(cdt, cdn, "linked_company_document", "");
			frappe.model.set_value(cdt, cdn, "linked_specification", "");
		} else if (row.document_source === "Item Specification") {
			frappe.model.set_value(cdt, cdn, "linked_company_document", "");
			frappe.model.set_value(cdt, cdn, "linked_drawing_revision", "");
		} else if (row.document_source === "Upload File") {
			frappe.model.set_value(cdt, cdn, "linked_company_document", "");
			frappe.model.set_value(cdt, cdn, "linked_drawing_revision", "");
			frappe.model.set_value(cdt, cdn, "linked_specification", "");
		}
	},

	linked_company_document(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.linked_company_document) {
			frappe.db.get_value(
				"PEPL Company Document",
				row.linked_company_document,
				["document_type", "document_type_other", "current_version_file",
				 "current_issue_date", "current_expiry_date", "current_reference_no"],
				(r) => {
					if (r) {
						frappe.model.set_value(cdt, cdn, "document_type",
							r.document_type === "Other" ? r.document_type_other : r.document_type);
						if (r.current_version_file) {
							frappe.model.set_value(cdt, cdn, "file_attach", r.current_version_file);
						}
						if (r.current_issue_date) {
							frappe.model.set_value(cdt, cdn, "issue_date", r.current_issue_date);
						}
						if (r.current_expiry_date) {
							frappe.model.set_value(cdt, cdn, "expiry_date", r.current_expiry_date);
						}
						if (r.current_reference_no) {
							frappe.model.set_value(cdt, cdn, "reference_no", r.current_reference_no);
						}
					}
				}
			);
		}
	}
});


frappe.ui.form.on("Vendor Approval Status", {
    refresh(frm) {
        const health_colors = {
            "Active": "green",
            "Expiring Soon": "orange",
            "Expired": "red",
            "No Expiry Set": "grey"
        };

        if (frm.doc.approval_health) {
            frm.dashboard.add_indicator(
                __(
                    "Approval Health: {0}",
                    [frm.doc.approval_health]
                ),
                health_colors[frm.doc.approval_health] || "grey"
            );
        }

        if (frm.doc.approval_warning) {
            frm.dashboard.add_comment(
                frm.doc.approval_warning,
                frm.doc.approval_health === "Expired"
                    ? "red"
                    : "orange",
                true
            );
        }
    }
});
