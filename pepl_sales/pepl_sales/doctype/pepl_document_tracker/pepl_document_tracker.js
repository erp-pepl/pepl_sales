frappe.ui.form.on("PEPL Document Tracker", {
	refresh(frm) {
		if (frm.doc.total_documents !== undefined) {
			frm.page.set_indicator(
				`${frm.doc.total_documents} Document(s)`,
				frm.doc.total_documents > 0 ? "blue" : "grey"
			);
		}

		// Visual sort buttons for Document Entries
		if (!frm.is_new() && frm.doc.document_entries && frm.doc.document_entries.length > 1) {
			frm.add_custom_button(__("Sort by Type"), function () {
				_sort_doc_entries(frm, "document_type");
			}, __("Sort"));

			frm.add_custom_button(__("Sort by Date"), function () {
				_sort_doc_entries(frm, "document_date");
			}, __("Sort"));

			frm.add_custom_button(__("Sort by Status"), function () {
				_sort_doc_entries(frm, "document_status");
			}, __("Sort"));

			frm.add_custom_button(__("Reset to Original"), function () {
				_sort_doc_entries(frm, "idx");
			}, __("Sort"));
		}
	}
});

function _sort_doc_entries(frm, field) {
	if (!frm.doc.document_entries) return;

	// Visual sort only — reorders display without saving to database
	const sorted = [...frm.doc.document_entries].sort((a, b) => {
		const av = a[field] || "";
		const bv = b[field] || "";
		if (av < bv) return -1;
		if (av > bv) return 1;
		return 0;
	});

	sorted.forEach((row, i) => {
		row.idx = i + 1;
	});

	frm.doc.document_entries = sorted;
	frm.refresh_field("document_entries");

	frappe.show_alert({
		message: __("Sorted by {0}. Visual only \u2014 reload page to reset.", [field]),
		indicator: "blue"
	}, 4);
}
