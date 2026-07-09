frappe.ui.form.on("PEPL Payment Tracker", {
	refresh(frm) {
		const colours = {
			"Pending Dispatch": "orange",
			"Dispatched": "blue",
			"R-Note Received": "blue",
			"I-Note Received": "blue",
			"JCC Issued": "blue",
			"Bills Submitted": "yellow",
			"CO7 Issued": "yellow",
			"Payment Received": "green",
			"Reconciled": "green",
			"Closed": "darkgrey"
		};
		if (frm.doc.payment_status) {
			frm.page.set_indicator(
				frm.doc.payment_status,
				colours[frm.doc.payment_status] || "grey"
			);
		}

		// MSME breach warning
		if (frm.doc.ageing_bucket === "45+ days (MSME breach)" &&
				frm.doc.payment_status !== "Reconciled" &&
				frm.doc.payment_status !== "Closed") {
			frm.dashboard.add_comment(
				__("MSME Alert: Payment is {0} days overdue. Legal interest applies beyond 45 days.",
					[frm.doc.days_outstanding]),
				"red",
				true
			);
		}
	}
});
