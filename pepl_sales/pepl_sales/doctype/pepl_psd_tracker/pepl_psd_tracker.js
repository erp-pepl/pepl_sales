frappe.ui.form.on("PEPL PSD Tracker", {
    refresh(frm) {
        pepl_render_psd_summary(frm);
    }
});


function pepl_render_psd_summary(frm) {
    const entries = frm.doc.psd_entries || [];
    const submissions = frm.doc.psd_submissions || [];

    const status_counts = entries.reduce(
        (counts, row) => {
            const status =
                row.psd_status || __("Blank");

            counts[status] =
                (counts[status] || 0) + 1;

            return counts;
        },
        {}
    );

    const total_amount = flt(
        frm.doc.total_psd_amount
    );

    const active_count = cint(
        frm.doc.active_entries_count
    );

    const today = frappe.datetime.str_to_obj(
        frappe.datetime.get_today()
    );

    const active_submissions = submissions.filter(
        row => cint(row.is_active) === 1
    );

    const expired = [];
    const expiring_soon = [];
    const valid = [];

    active_submissions.forEach(row => {
        if (!row.validity_date) {
            return;
        }

        const validity =
            frappe.datetime.str_to_obj(
                row.validity_date
            );

        const days = Math.floor(
            (validity - today)
            / (1000 * 60 * 60 * 24)
        );

        const detail = {
            type:
                row.instrument_type
                || __("Instrument"),
            validity_date:
                row.validity_date,
            days
        };

        if (days < 0) {
            expired.push(detail);
        } else if (days <= 30) {
            expiring_soon.push(detail);
        } else {
            valid.push(detail);
        }
    });

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

    frm.dashboard.add_indicator(
        __("Active Instruments: {0}", [
            active_submissions.length
        ]),
        active_submissions.length
            ? "blue"
            : "grey"
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
                status_counts.Pending
            ]),
            "orange"
        );
    }

    if (expired.length) {
        frm.dashboard.add_indicator(
            __("Expired Instruments: {0}", [
                expired.length
            ]),
            "red"
        );
    }

    if (expiring_soon.length) {
        frm.dashboard.add_indicator(
            __("Expiring within 30 Days: {0}", [
                expiring_soon.length
            ]),
            "orange"
        );
    }

    const expiry_attention = [
        ...expired,
        ...expiring_soon
    ];

    if (expiry_attention.length) {
        const details = expiry_attention
            .map(row =>
                __(
                    "{0} — {1} — {2} day(s)",
                    [
                        row.type,
                        frappe.datetime.str_to_user(
                            row.validity_date
                        ),
                        row.days
                    ]
                )
            )
            .join("<br>");

        frm.dashboard.add_comment(
            __(
                "PSD instrument expiry attention:<br>{0}",
                [details]
            ),
            expired.length ? "red" : "orange",
            true
        );
    }
}
