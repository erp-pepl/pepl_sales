frappe.ui.form.on("PEPL RM Group", {
	refresh(frm) {
		if (frm.doc.is_active) {
			frm.page.set_indicator("Active", "green");
		} else {
			frm.page.set_indicator("Inactive", "grey");
		}
	}
});
