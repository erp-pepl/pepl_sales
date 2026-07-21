
frappe.ui.form.on("PEPL Tender", {
	refresh(frm) {
		const status_colors = {
                        "Draft": "grey",
                        "Active Bid": "blue",
                        "Costing": "orange",
                        "Costed": "cyan",
                        "Submitted": "yellow",
			"Won": "green",
			"Partially Won": "green",
			"Order Received": "purple",
			"Lost": "red",
			"No Bid": "grey",
			"Cancelled": "grey",
			"Re-tendered": "orange"
		};
		if (frm.doc.status) {
			frm.page.set_indicator(frm.doc.status, status_colors[frm.doc.status]);
		}

		// Deadline urgency indicator
		if (frm.doc.bid_submission_deadline && frm.doc.status === "Active Bid") {
			const deadline = frappe.datetime.str_to_obj(frm.doc.bid_submission_deadline);
			const now = new Date();
			const days_left = Math.floor((deadline - now) / (1000 * 60 * 60 * 24));

			if (days_left < 0) {
				frm.dashboard.add_indicator(__("DEADLINE PASSED"), "red");
			} else if (days_left <= 1) {
				frm.dashboard.add_indicator(__("Deadline in {0} day(s)", [days_left]), "red");
			} else if (days_left <= 3) {
				frm.dashboard.add_indicator(__("Deadline in {0} days", [days_left]), "orange");
			} else if (days_left <= 7) {
				frm.dashboard.add_indicator(__("Deadline in {0} days", [days_left]), "yellow");
			}
		}

		// Auto-Generate Document Checklist button
		if (frm.doc.docstatus === 0 && !frm.is_new() && frm.doc.items && frm.doc.items.length > 0) {
			frm.add_custom_button(__("Auto-Generate Document Checklist"), function() {
				frappe.call({
					method: "pepl_sales.pepl_sales.doctype.pepl_tender.pepl_tender.auto_populate_bid_documents",
					args: { tender_name: frm.doc.name },
					callback: function(r) {
						if (r.message) {
							frappe.show_alert({
								message: __("Added {0} required documents to checklist (total {1})",
									[r.message.added, r.message.total_required]),
								indicator: "green"
							});
							frm.reload_doc();
						}
					}
				});
			}, __("Documents"));
		}

		// RED warning dashboard indicator for PO Schedule items not in Won list
		if (frm.doc.po_schedule && frm.doc.po_schedule.length > 0) {
			const invalid_items = frm.doc.po_schedule.filter(s =>
				s.item && s.is_in_won_list === 0
			);

			if (invalid_items.length > 0) {
				const item_names = [...new Set(invalid_items.map(s => s.item))].join(", ");
				frm.dashboard.add_indicator(
					__("\u26a0 {0} PO Schedule item(s) NOT in Won list: {1}",
						[invalid_items.length, item_names]),
					"red"
				);
			}
		}

		// Create Sales Order button — uses PO Schedule lines
		const can_create_so = !frm.is_new()
			&& [0, 1].includes(frm.doc.docstatus)
			&& (frm.doc.status === "Won" || frm.doc.status === "Partially Won")
			&& frm.doc.customer_po_received === 1
			&& frm.doc.po_number
			&& frm.doc.po_date
                        && frm.doc.po_schedule
			&& frm.doc.po_schedule.length > 0
			&& !frm.doc.linked_sales_order;

		if (can_create_so) {
			frm.add_custom_button(__("Create Sales Order"), function() {
				const lines_count = (frm.doc.po_schedule || []).length;

				frappe.confirm(
					__("Create Sales Order with {0} delivery lines? Each PO Schedule line becomes a separate SO line item with its own delivery date. You can edit values in the Sales Order before submitting.", [lines_count]),
					function() {
						frappe.call({
							method: "pepl_sales.pepl_sales.doctype.pepl_tender.pepl_tender.create_sales_order_from_tender",
							args: { tender_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Creating Sales Order..."),
							callback: function(r) {
								if (r.message) {
									frappe.show_alert({
										message: __("Sales Order {0} created with {1} delivery line(s)",
											[r.message.sales_order, r.message.lines_added]),
										indicator: "green"
									});
									setTimeout(() => {
										frappe.set_route("Form", "Sales Order", r.message.sales_order);
									}, 1500);
								}
							}
						});
					}
				);
			}, __("Order")).addClass("btn-primary");
		}

		// If SO already linked — View Sales Order button + indicator
		if (frm.doc.linked_sales_order) {
			frm.add_custom_button(__("View Sales Order"), function() {
				frappe.set_route("Form", "Sales Order", frm.doc.linked_sales_order);
			}, __("Order"));

			frm.dashboard.add_indicator(
				__("Order Received: {0}", [frm.doc.linked_sales_order]),
				"purple"
			);
		}

		// Financial summary in dashboard
		if (!frm.is_new() && frm.doc.total_estimated_value) {
			const win_info = frm.doc.win_rate ? ` | Win Rate: ${frm.doc.win_rate.toFixed(1)}%` : "";
			const est = frappe.format(frm.doc.total_estimated_value, { fieldtype: "Currency" });
			const bid = frappe.format(frm.doc.total_bid_value || 0, { fieldtype: "Currency" });
			frm.dashboard.add_comment(
				`Est: ${est} | Bid: ${bid}${win_info}`,
				"blue",
				true
			);
		}
	},

	customer(frm) {
		if (frm.doc.customer) {
			frappe.db.get_value("Customer", frm.doc.customer, "customer_group", (r) => {
				if (r && r.customer_group) {
					frm.set_value("customer_group", r.customer_group);

					if (r.customer_group.includes("Railways")) {
						frm.set_value("sector", "Railways");
					} else if (r.customer_group.includes("Defence")) {
						frm.set_value("sector", "Defence");
					} else if (r.customer_group.includes("Private")) {
						frm.set_value("sector", "Private");
					}

					frm.set_value("sub_sector", r.customer_group);
				}
			});
		}
	},

	bid_securing_declaration(frm) {
		if (frm.doc.bid_securing_declaration) {
			frm.set_value("emd_required", 0);
		}
	},

	emd_required(frm) {
		if (frm.doc.emd_required) {
			frm.set_value("bid_securing_declaration", 0);
		}
	},

	customer_po_received(frm) {
		if (frm.doc.customer_po_received && !frm.doc.po_date) {
			frm.set_value("po_date", frappe.datetime.get_today());
		}
	}
});

frappe.ui.form.on("PEPL Tender Item", {
	quantity(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "estimated_total_value",
			flt(row.quantity) * flt(row.estimated_unit_price));
		frappe.model.set_value(cdt, cdn, "our_bid_total_value",
			flt(row.quantity) * flt(row.our_bid_unit_price));
	},

	estimated_unit_price(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "estimated_total_value",
			flt(row.quantity) * flt(row.estimated_unit_price));
	},

	our_bid_unit_price(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "our_bid_total_value",
			flt(row.quantity) * flt(row.our_bid_unit_price));
	}
});

// PO Schedule child table — real-time recalc + item-in-won-list warning
frappe.ui.form.on("PEPL Tender PO Schedule", {
	item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item) return;

		// Warn if item is not in the Won items list
		const won_items = (frm.doc.items || [])
			.filter(i =>
                                ["Won", "Partially Won"].includes(i.outcome)
                        )
			.map(i => i.item);

		if (won_items.length > 0 && !won_items.includes(row.item)) {
			frappe.show_alert({
				message: __("\u26a0 Warning: Item {0} is NOT in the Won items list of this tender. Please verify.", [row.item]),
				indicator: "red"
			}, 6);
		}
	},

	po_quantity(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "po_total",
			flt(row.po_quantity) * flt(row.po_rate));
	},

	po_rate(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "po_total",
			flt(row.po_quantity) * flt(row.po_rate));
	}
});


// Customer-specific Vendor Approval Gate
frappe.ui.form.on("PEPL Tender", {
    refresh(frm) {
        const approval_issues = (frm.doc.items || []).filter(row =>
            ["Expired", "Expiring Soon", "Missing"].includes(
                row.vendor_approval_health
            )
        );

        if (approval_issues.length) {
            const labels = approval_issues
                .map(row =>
                    `${row.item}: ${row.vendor_approval_health}`
                )
                .join(", ");

            frm.dashboard.add_indicator(
                __(
                    "Vendor Approval attention required for {0} item(s)",
                    [approval_issues.length]
                ),
                "orange"
            );

            frm.dashboard.add_comment(
                __("Approval warnings: {0}", [labels]),
                "orange",
                true
            );
        }
    }
});


frappe.ui.form.on("PEPL Tender Item", {
    item(frm, cdt, cdn) {
        refresh_vendor_approval_for_tender_item(frm, cdt, cdn);
    }
});


async function refresh_vendor_approval_for_tender_item(frm, cdt, cdn) {
    const row = locals[cdt][cdn];

    if (
        !frm.doc.customer
        || !frm.doc.sector
        || !row.item
    ) {
        return;
    }

    try {
        const response = await frappe.call({
            method: "pepl_sales.pepl_sales.doctype.vendor_approval_status.vendor_approval_status.get_approval_status_for_item",
            args: {
                customer: frm.doc.customer,
                item: row.item,
                sector: frm.doc.sector
            }
        });

        const approval = response.message || {};

        await frappe.model.set_value(
            cdt,
            cdn,
            "vendor_approval_record",
            approval.name || ""
        );

        await frappe.model.set_value(
            cdt,
            cdn,
            "vendor_approval_stage",
            approval.stage || "No Record"
        );

        await frappe.model.set_value(
            cdt,
            cdn,
            "vendor_approval_health",
            approval.health || "Missing"
        );

        await frappe.model.set_value(
            cdt,
            cdn,
            "vendor_approval_expiry",
            approval.expiry_date || ""
        );

        await frappe.model.set_value(
            cdt,
            cdn,
            "vendor_approval_warning",
            approval.warning || ""
        );

        if (
            ["Expired", "Expiring Soon", "Missing"].includes(
                approval.health
            )
        ) {
            frappe.show_alert(
                {
                    message: approval.warning
                        || __(
                            "Vendor Approval requires attention for {0}.",
                            [row.item]
                        ),
                    indicator: "orange"
                },
                8
            );
        }
    } catch (error) {
        frappe.show_alert(
            {
                message: __(
                    "Unable to retrieve Vendor Approval for {0}.",
                    [row.item]
                ),
                indicator: "orange"
            },
            6
        );
    }
}


// PEPL COMPETITOR WORKFLOW HELPERS
function pepl_get_all_competitor_rows(frm) {
    const items_by_code = {};

    (frm.doc.items || []).forEach(item_row => {
        if (item_row.item) {
            items_by_code[item_row.item] = item_row;
        }
    });

    return (frm.doc.competitor_entries || []).map(row => ({
        item: items_by_code[row.item] || null,
        row
    }));
}

function pepl_add_competitor_actions(frm) {
    if (frm.is_new()) {
        return;
    }

    frm.add_custom_button(
        __("Calculate Competitor Analysis"),
        function () {
            const rows = pepl_get_all_competitor_rows(frm);

            if (!rows.length) {
                frappe.msgprint(
                    __("Add at least one competitor row before calculating.")
                );
                return;
            }

            frm.save()
                .then(() => frm.reload_doc())
                .then(() => {
                    frappe.show_alert(
                        {
                            message: __(
                                "Competitor analysis recalculated successfully."
                            ),
                            indicator: "green"
                        },
                        6
                    );
                });
        },
        __("Competitor Analysis")
    );

    if (
        ["Won", "Partially Won", "Lost", "Cancelled"]
            .includes(frm.doc.status)
    ) {
        frm.add_custom_button(
            __("Validate Outcome Analysis"),
            function () {
                const summary = [
                    __("Status: {0}", [frm.doc.status || "-"]),
                    __("Items Won/Partially Won: {0}", [
                        frm.doc.items_won || 0
                    ]),
                    __("Items Lost: {0}", [
                        frm.doc.items_lost || 0
                    ]),
                    __("PEPL Rank: {0}", [
                        frm.doc.our_overall_rank || "-"
                    ]),
                    __("Winning Competitor: {0}", [
                        frm.doc.winning_competitor || "-"
                    ]),
                    __("Winning Price: {0}", [
                        frappe.format(
                            frm.doc.winning_price || 0,
                            { fieldtype: "Currency" }
                        )
                    ])
                ].join("<br>");

                frappe.confirm(
                    __(
                        "Finalize this Tender outcome?<br><br>{0}",
                        [summary]
                    ),
                    function () {
                        frm.save()
                            .then(() => frm.reload_doc())
                            .then(() => {
                                frappe.show_alert(
                                    {
                                        message: __(
                                            "Tender outcome finalized successfully."
                                        ),
                                        indicator: "green"
                                    },
                                    6
                                );
                            });
                    }
                );
            },
            __("Competitor Analysis")
        );
    }
}

function pepl_add_competitor_guidance(frm) {
    const entries = pepl_get_all_competitor_rows(frm);

    if (!entries.length) {
        return;
    }

    const pepl_rows = entries.filter(entry => entry.row.is_pepl);

    const winner_rows = entries.filter(entry =>
        entry.row.is_winner
        || entry.row.buyer_selected
        || entry.row.is_l1
        || Number(entry.row.rank_number || 0) === 1
    );

    const unpriced_rows = entries.filter(entry =>
        Number(entry.row.competitor_price || 0) <= 0
        && Number(entry.row.evaluated_unit_rate || 0) <= 0
        && Number(entry.row.total_bid_value || 0) <= 0
    );

    if (!pepl_rows.length) {
        frm.dashboard.add_indicator(
            __("No competitor row is marked Is PEPL"),
            "orange"
        );
    }

    if (!winner_rows.length) {
        frm.dashboard.add_indicator(
            __("No L1, Winner, or Buyer Selected row is identified"),
            "orange"
        );
    }

    if (unpriced_rows.length) {
        frm.dashboard.add_indicator(
            __(
                "{0} competitor row(s) have no evaluated price",
                [unpriced_rows.length]
            ),
            "orange"
        );
    }

    if (
        ["Won", "Partially Won", "Lost"].includes(frm.doc.status)
        && !frm.doc.financial_result_attachment
    ) {
        frm.dashboard.add_indicator(
            __("Official financial-result attachment is missing"),
            "orange"
        );
    }

    if (frm.doc.competitor_analysis_completed) {
        frm.dashboard.add_indicator(
            __("Competitor Analysis Finalised"),
            "green"
        );
    }
}

frappe.ui.form.on("PEPL Tender", {
    refresh(frm) {
        pepl_add_competitor_actions(frm);
        pepl_add_competitor_guidance(frm);
    }
});

frappe.ui.form.on("PEPL Tender Item Competitor", {
    rank(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const match = String(row.rank || "")
            .trim()
            .toUpperCase()
            .match(/^L\s*0*(\d+)$/);

        frappe.model.set_value(
            cdt,
            cdn,
            "rank_number",
            match ? Number(match[1]) : 0
        );

        frappe.model.set_value(
            cdt,
            cdn,
            "is_l1",
            match && Number(match[1]) === 1 ? 1 : 0
        );
    }
});

