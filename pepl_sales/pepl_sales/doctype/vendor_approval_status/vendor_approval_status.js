frappe.ui.form.on("Vendor Approval Status", {
	refresh(frm) {
		set_stage_indicator(frm);
		show_approval_health(frm);

		if (
			frm.doc.sector
			&& (frm.doc.railways_stage || frm.doc.defence_stage)
		) {
			frm.add_custom_button(
				__("Show Required Documents"),
				() => show_required_documents(frm),
				__("Documents")
			);
		}

		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Synchronize Requirements"),
				() => synchronize_requirements(frm),
				__("Documents")
			);
		}
	},

	sector(frm) {
		if (frm.doc.sector === "Railways") {
			frm.set_value("defence_stage", "");
		} else if (frm.doc.sector === "Defence") {
			frm.set_value("railways_stage", "");
		}
	},

	railways_stage(frm) {
		if (frm.doc.sector === "Railways") {
			frm.dirty();
		}
	},

	defence_stage(frm) {
		if (frm.doc.sector === "Defence") {
			frm.dirty();
		}
	}
});


frappe.ui.form.on("Vendor Approval Document", {
	document_source(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (row.document_source === "Company Library") {
			frappe.model.set_value(
				cdt,
				cdn,
				"linked_drawing_revision",
				""
			);
			frappe.model.set_value(
				cdt,
				cdn,
				"linked_specification",
				""
			);
		} else if (row.document_source === "Item Drawing") {
			frappe.model.set_value(
				cdt,
				cdn,
				"linked_company_document",
				""
			);
			frappe.model.set_value(
				cdt,
				cdn,
				"linked_specification",
				""
			);
		} else if (
			row.document_source === "Item Specification"
		) {
			frappe.model.set_value(
				cdt,
				cdn,
				"linked_company_document",
				""
			);
			frappe.model.set_value(
				cdt,
				cdn,
				"linked_drawing_revision",
				""
			);
		} else if (row.document_source === "Upload File") {
			frappe.model.set_value(
				cdt,
				cdn,
				"linked_company_document",
				""
			);
			frappe.model.set_value(
				cdt,
				cdn,
				"linked_drawing_revision",
				""
			);
			frappe.model.set_value(
				cdt,
				cdn,
				"linked_specification",
				""
			);
		}
	},

	linked_company_document(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		if (!row.linked_company_document) {
			return;
		}

		frappe.db.get_value(
			"PEPL Company Document",
			row.linked_company_document,
			[
				"document_type",
				"document_type_other",
				"current_version_file",
				"current_issue_date",
				"current_expiry_date",
				"current_reference_no"
			]
		).then((response) => {
			const values = response.message || {};

			frappe.model.set_value(
				cdt,
				cdn,
				"document_type",
				values.document_type === "Other"
					? values.document_type_other
					: values.document_type
			);

			if (values.current_version_file) {
				frappe.model.set_value(
					cdt,
					cdn,
					"file_attach",
					values.current_version_file
				);
			}

			if (values.current_issue_date) {
				frappe.model.set_value(
					cdt,
					cdn,
					"issue_date",
					values.current_issue_date
				);
			}

			if (values.current_expiry_date) {
				frappe.model.set_value(
					cdt,
					cdn,
					"expiry_date",
					values.current_expiry_date
				);
			}

			if (values.current_reference_no) {
				frappe.model.set_value(
					cdt,
					cdn,
					"reference_no",
					values.current_reference_no
				);
			}
		});
	}
});


function set_stage_indicator(frm) {
	if (
		frm.doc.sector === "Railways"
		&& frm.doc.railways_stage
	) {
		const colors = {
			"Unapproved": "red",
			"Developmental": "orange",
			"Approved": "green"
		};

		frm.page.set_indicator(
			frm.doc.railways_stage,
			colors[frm.doc.railways_stage] || "grey"
		);
	} else if (
		frm.doc.sector === "Defence"
		&& frm.doc.defence_stage
	) {
		const colors = {
			"Source Development": "orange",
			"Approved / Established": "green"
		};

		frm.page.set_indicator(
			frm.doc.defence_stage,
			colors[frm.doc.defence_stage] || "grey"
		);
	}
}


function show_approval_health(frm) {
	const colors = {
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
			colors[frm.doc.approval_health] || "grey"
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


function show_required_documents(frm) {
	frappe.call({
		method: (
			"pepl_sales.pepl_sales.doctype."
			+ "vendor_approval_status.vendor_approval_status."
			+ "get_required_documents"
		),
		args: {
			sector: frm.doc.sector,
			stage: (
				frm.doc.sector === "Railways"
					? frm.doc.railways_stage
					: frm.doc.defence_stage
			)
		},
		callback(response) {
			const documents = response.message || [];

			if (!documents.length) {
				frappe.msgprint({
					title: __("Required Documents"),
					message: __(
						"No active requirements are configured "
						+ "for this sector and stage."
					),
					indicator: "orange"
				});
				return;
			}

			const list = documents
				.map((document_name) => {
					return `<li>${frappe.utils.escape_html(
						document_name
					)}</li>`;
				})
				.join("");

			frappe.msgprint({
				title: __("Required Documents for This Stage"),
				message: `<ul>${list}</ul>`,
				indicator: "blue"
			});
		}
	});
}


function synchronize_requirements(frm) {
	if (frm.is_new()) {
		frappe.msgprint(
			__("Save the Vendor Approval record first.")
		);
		return;
	}

	frappe.call({
		method: (
			"pepl_sales.pepl_sales.doctype."
			+ "vendor_approval_status.vendor_approval_status."
			+ "synchronize_requirements"
		),
		args: {
			name: frm.doc.name
		},
		freeze: true,
		freeze_message: __("Synchronizing requirements..."),
		callback(response) {
			const result = response.message || {};

			frappe.show_alert({
				message: __(
					"Requirements synchronized: {0} created, "
					+ "{1} updated, {2} historical.",
					[
						result.created || 0,
						result.updated || 0,
						result.historical || 0
					]
				),
				indicator: "green"
			});

			frm.reload_doc();
		}
	});
}
