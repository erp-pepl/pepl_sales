frappe.ui.form.on("PEPL Payment Tracker", {
    refresh(frm) {
        pepl_render_payment_summary(frm);
    }
});


function pepl_render_payment_summary(frm) {
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
            colours[frm.doc.payment_status]
                || "grey"
        );
    }

    const invoice_amount =
        flt(frm.doc.invoice_amount);

    const received =
        flt(frm.doc.total_amount_received);

    const outstanding =
        flt(frm.doc.total_outstanding);

    const reconciled =
        flt(frm.doc.amount_reconciled);

    const deductions =
        flt(frm.doc.tds_deducted)
        + flt(frm.doc.sd_deducted)
        + flt(frm.doc.ld_deducted)
        + flt(frm.doc.other_deductions);

    const receipts =
        frm.doc.payment_receipts || [];

    const payment_percent = invoice_amount > 0
        ? Math.min(
            100,
            received / invoice_amount * 100
        )
        : 0;

    frm.dashboard.add_indicator(
        __("Receipts: {0}", [
            receipts.length
        ]),
        receipts.length ? "blue" : "grey"
    );

    frm.dashboard.add_indicator(
        __("Payment Progress: {0}%", [
            payment_percent.toFixed(1)
        ]),
        payment_percent >= 100
            ? "green"
            : payment_percent > 0
                ? "blue"
                : "orange"
    );

    frm.dashboard.add_indicator(
        __("Outstanding: {0}", [
            format_currency(
                outstanding,
                frm.doc.currency || "INR"
            )
        ]),
        outstanding > 0 ? "orange" : "green"
    );

    frm.dashboard.add_indicator(
        __("Deductions: {0}", [
            format_currency(
                deductions,
                frm.doc.currency || "INR"
            )
        ]),
        deductions > 0 ? "orange" : "grey"
    );

    frm.dashboard.add_indicator(
        __("Reconciled: {0}", [
            format_currency(
                reconciled,
                frm.doc.currency || "INR"
            )
        ]),
        reconciled > 0 ? "green" : "grey"
    );

    const summary = [
        __(
            "Invoice: {0}",
            [
                format_currency(
                    invoice_amount,
                    frm.doc.currency || "INR"
                )
            ]
        ),
        __(
            "Received: {0}",
            [
                format_currency(
                    received,
                    frm.doc.currency || "INR"
                )
            ]
        ),
        __(
            "Outstanding: {0}",
            [
                format_currency(
                    outstanding,
                    frm.doc.currency || "INR"
                )
            ]
        ),
        __(
            "Ageing: {0} day(s) — {1}",
            [
                cint(frm.doc.days_outstanding),
                frm.doc.ageing_bucket || "-"
            ]
        )
    ].join(" | ");

    frm.dashboard.add_comment(
        summary,
        outstanding > 0 ? "blue" : "green",
        true
    );

    if (
        frm.doc.ageing_bucket
            === "45+ days (MSME breach)"
        && !["Reconciled", "Closed"].includes(
            frm.doc.payment_status
        )
    ) {
        frm.dashboard.add_comment(
            __(
                "MSME Alert: Payment is {0} days overdue. "
                + "Legal interest applies beyond 45 days.",
                [frm.doc.days_outstanding]
            ),
            "red",
            true
        );
    }
}
