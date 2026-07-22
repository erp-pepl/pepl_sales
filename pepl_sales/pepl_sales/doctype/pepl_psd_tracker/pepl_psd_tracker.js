frappe.ui.form.on("PEPL PSD Tracker", {
    refresh(frm) {
        const entries = frm.doc.psd_entries || [];

        const status_counts = entries.reduce((counts, row) => {
            const status = row.psd_status || __("Blank");
            counts[status] = (counts[status] || 0) + 1;
            return counts;
        }, {});

        const total_amount = flt(
            frm.doc.total_psd_amount
        );

        const active_count = cint(
            frm.doc.active_entries_count
        );

        frm.page.set_indicator(
            __("Total PSD: {0}", [
                format_currency(
                    total_amount,
                    frm.doc.currency || "INR"
                )
            ]),
            total_amount > 0 ? "blue" : "grey"
        );

        frm.dashboard.add_indicator(
            __("Active Entries: {0}", [
                active_count
            ]),
            active_count > 0 ? "orange" : "green"
        );

        if (status_counts["PSD Not Required"]) {
            frm.dashboard.add_indicator(
                __("PSD Not Required: {0}", [
                    status_counts["PSD Not Required"]
                ]),
                "green"
            );
        }

        if (status_counts["Pending"]) {
            frm.dashboard.add_indicator(
                __("Pending PSD Entries: {0}", [
                    status_counts["Pending"]
                ]),
                "orange"
            );
        }
    }
});
