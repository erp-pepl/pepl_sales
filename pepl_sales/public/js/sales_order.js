frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        pepl_render_sales_order_readiness(frm);
    },

    customer(frm) {
        pepl_render_sales_order_readiness(frm);
    },

    custom_sector(frm) {
        pepl_render_sales_order_readiness(frm);
    }
});


async function pepl_render_sales_order_readiness(frm) {
    const items = frm.doc.items || [];
    const sector = frm.doc.custom_sector || "";

    if (!items.length) {
        frm.dashboard.add_indicator(
            __("Product Readiness: No Items"),
            "grey"
        );
        return;
    }

    const unique_items = [
        ...new Set(
            items
                .map(row => row.item_code)
                .filter(Boolean)
        )
    ];

    if (!unique_items.length) {
        frm.dashboard.add_indicator(
            __("Product Readiness: No Valid Items"),
            "orange"
        );
        return;
    }

    if (!["Railways", "Defence"].includes(sector)) {
        frm.dashboard.add_indicator(
            __("Product Readiness: Not Applicable for {0}", [
                sector || __("Unspecified Sector")
            ]),
            "blue"
        );

        frm.dashboard.add_comment(
            __(
                "{0} item(s) present. Customer-specific Vendor "
                + "Approval checks apply to Railways and Defence.",
                [unique_items.length]
            ),
            "blue",
            true
        );

        return;
    }

    if (!frm.doc.customer) {
        frm.dashboard.add_indicator(
            __("Product Readiness: Customer Required"),
            "orange"
        );
        return;
    }

    const results = [];

    for (const item_code of unique_items) {
        try {
            const response = await frappe.call({
                method:
                    "pepl_sales.pepl_sales.doctype."
                    + "vendor_approval_status.vendor_approval_status."
                    + "get_approval_status_for_item",
                args: {
                    customer: frm.doc.customer,
                    item: item_code,
                    sector
                }
            });

            const approval = response.message || {};

            results.push({
                item: item_code,
                stage: approval.stage || __("No Record"),
                health: approval.health || __("Missing"),
                expiry_date: approval.expiry_date || "",
                warning: approval.warning || ""
            });

        } catch (error) {
            results.push({
                item: item_code,
                stage: __("Lookup Failed"),
                health: __("Missing"),
                expiry_date: "",
                warning: __(
                    "Unable to retrieve Vendor Approval."
                )
            });
        }
    }

    const healthy = results.filter(
        row => ["Active", "No Expiry Set"].includes(
            row.health
        )
    );

    const attention = results.filter(
        row => !["Active", "No Expiry Set"].includes(
            row.health
        )
    );

    const ready = attention.length === 0;

    frm.dashboard.add_indicator(
        __("Product Readiness: {0}", [
            ready ? __("READY") : __("ATTENTION REQUIRED")
        ]),
        ready ? "green" : "orange"
    );

    frm.dashboard.add_indicator(
        __("Healthy Approvals: {0}/{1}", [
            healthy.length,
            results.length
        ]),
        healthy.length === results.length
            ? "green"
            : "orange"
    );

    if (attention.length) {
        const detail = attention
            .map(row => {
                const parts = [
                    row.item,
                    row.stage,
                    row.health
                ];

                if (row.expiry_date) {
                    parts.push(
                        __("Expiry: {0}", [
                            frappe.datetime.str_to_user(
                                row.expiry_date
                            )
                        ])
                    );
                }

                if (row.warning) {
                    parts.push(row.warning);
                }

                return parts.filter(Boolean).join(" — ");
            })
            .join("<br>");

        frm.dashboard.add_comment(
            __(
                "Product readiness issues:<br>{0}",
                [detail]
            ),
            "orange",
            true
        );
    } else {
        frm.dashboard.add_comment(
            __(
                "All {0} Sales Order item(s) have healthy "
                + "customer-specific Vendor Approval.",
                [results.length]
            ),
            "green",
            true
        );
    }
}
