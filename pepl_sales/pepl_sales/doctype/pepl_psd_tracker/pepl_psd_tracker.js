frappe.ui.form.on("PEPL PSD Tracker", {
	refresh(frm) {
		if (frm.doc.total_psd_amount) {
			frm.page.set_indicator(
				`Total PSD: ₹${frappe.format(frm.doc.total_psd_amount, { fieldtype: "Currency" })}`,
				"blue"
			);
		}
	}
});
