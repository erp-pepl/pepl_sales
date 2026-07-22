frappe.ui.form.on("PEPL Document Tracker", {
    refresh(frm) {
        _render_document_summary(frm);
        _add_document_sort_buttons(frm);
    }
});


function _render_document_summary(frm) {
    const entries = frm.doc.document_entries || [];

    const completed_statuses = new Set([
        "Received",
        "Filed"
    ]);

    const received_count = entries.filter(
        row => completed_statuses.has(
            row.document_status
        )
    ).length;

    const pending_count = entries.filter(
        row => !completed_statuses.has(
            row.document_status
        )
    ).length;

    const pending_required = entries.filter(
        row =>
            cint(row.is_required) === 1
            && !completed_statuses.has(
                row.document_status
            )
    );

    const payment_blocked =
        pending_required.length > 0;

    frm.page.set_indicator(
        __("{0} Document(s)", [
            entries.length
        ]),
        entries.length > 0 ? "blue" : "grey"
    );

    frm.dashboard.add_indicator(
        __("Received / Filed: {0}", [
            received_count
        ]),
        received_count > 0 ? "green" : "grey"
    );

    frm.dashboard.add_indicator(
        __("Pending: {0}", [
            pending_count
        ]),
        pending_count > 0 ? "orange" : "green"
    );

    frm.dashboard.add_indicator(
        __("Payment Blocked: {0}", [
            payment_blocked
                ? __("Yes")
                : __("No")
        ]),
        payment_blocked ? "red" : "green"
    );

    if (pending_required.length) {
        frm.dashboard.add_comment(
            __(
                "Pending required documents: {0}",
                [
                    pending_required
                        .map(row =>
                            row.document_type
                            || __("Unnamed Document")
                        )
                        .join(", ")
                ]
            ),
            "red",
            true
        );
    }
}


function _add_document_sort_buttons(frm) {
    const entries = frm.doc.document_entries || [];

    if (frm.is_new() || entries.length <= 1) {
        return;
    }

    frm.add_custom_button(
        __("Sort by Type"),
        () => _sort_doc_entries(
            frm,
            "document_type"
        ),
        __("Sort")
    );

    frm.add_custom_button(
        __("Sort by Date"),
        () => _sort_doc_entries(
            frm,
            "document_date"
        ),
        __("Sort")
    );

    frm.add_custom_button(
        __("Sort by Status"),
        () => _sort_doc_entries(
            frm,
            "document_status"
        ),
        __("Sort")
    );

    frm.add_custom_button(
        __("Reset to Original"),
        () => _sort_doc_entries(
            frm,
            "idx"
        ),
        __("Sort")
    );
}


function _sort_doc_entries(frm, field) {
    const entries = frm.doc.document_entries || [];

    const sorted = [...entries].sort(
        (a, b) => {
            const av = a[field] || "";
            const bv = b[field] || "";

            if (av < bv) return -1;
            if (av > bv) return 1;
            return 0;
        }
    );

    sorted.forEach((row, index) => {
        row.idx = index + 1;
    });

    frm.doc.document_entries = sorted;
    frm.refresh_field("document_entries");

    frappe.show_alert(
        {
            message: __(
                "Sorted by {0}. Visual only — reload "
                + "the page to reset.",
                [field]
            ),
            indicator: "blue"
        },
        4
    );
}
