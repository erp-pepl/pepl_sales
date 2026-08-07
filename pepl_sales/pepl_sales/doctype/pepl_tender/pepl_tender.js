
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

// PO Schedule child table — real-time flagging and aggregation.
// Server-side recalculation remains authoritative.
function pepl_get_awarded_quantity(tender_item) {
        if (!tender_item) {
                return 0;
        }

        if (flt(tender_item.awarded_quantity) > 0) {
                return flt(tender_item.awarded_quantity);
        }

        if (
                tender_item.outcome === "Partially Won"
                && flt(tender_item.award_share_percent) > 0
        ) {
                return (
                        flt(tender_item.quantity)
                        * flt(tender_item.award_share_percent)
                        / 100
                );
        }

        if (tender_item.outcome === "Won") {
                return flt(tender_item.quantity);
        }

        return 0;
}


function pepl_recalculate_po_schedule(frm) {
        let parent_total = 0;
        const tender_items = {};

        (frm.doc.items || []).forEach(tender_item => {
                if (tender_item.item) {
                        tender_items[tender_item.item] = tender_item;
                }
        });

        (frm.doc.po_schedule || []).forEach(schedule_row => {
                const tender_item = tender_items[schedule_row.item];

                const is_awarded = Boolean(
                        tender_item
                        && ["Won", "Partially Won"].includes(
                                tender_item.outcome
                        )
                        && pepl_get_awarded_quantity(tender_item) > 0
                );

                const line_total = (
                        flt(schedule_row.po_quantity)
                        * flt(schedule_row.po_rate)
                );

                if (
                        Number(schedule_row.is_in_won_list || 0)
                        !== Number(is_awarded)
                ) {
                        frappe.model.set_value(
                                schedule_row.doctype,
                                schedule_row.name,
                                "is_in_won_list",
                                is_awarded ? 1 : 0
                        );
                }

                if (flt(schedule_row.po_total) !== line_total) {
                        frappe.model.set_value(
                                schedule_row.doctype,
                                schedule_row.name,
                                "po_total",
                                line_total
                        );
                }

                parent_total += line_total;
        });

        if (flt(frm.doc.po_amount_received) !== parent_total) {
                frm.set_value(
                        "po_amount_received",
                        parent_total
                );
        }
}


frappe.ui.form.on("PEPL Tender", {
        po_schedule_add(frm) {
                pepl_recalculate_po_schedule(frm);
        },

        po_schedule_remove(frm) {
                pepl_recalculate_po_schedule(frm);
        }
});


frappe.ui.form.on("PEPL Tender PO Schedule", {
        item(frm, cdt, cdn) {
                const row = locals[cdt][cdn];

                pepl_recalculate_po_schedule(frm);

                if (!row.item) {
                        return;
                }

                const tender_item = (frm.doc.items || []).find(
                        item_row => item_row.item === row.item
                );

                const is_awarded = Boolean(
                        tender_item
                        && ["Won", "Partially Won"].includes(
                                tender_item.outcome
                        )
                        && pepl_get_awarded_quantity(tender_item) > 0
                );

                if (!is_awarded) {
                        frappe.show_alert(
                                {
                                        message: __(
                                                "Warning: Item {0} is not "
                                                + "an awarded Tender item.",
                                                [row.item]
                                        ),
                                        indicator: "red"
                                },
                                6
                        );
                }
        },

        po_quantity(frm) {
                pepl_recalculate_po_schedule(frm);
        },

        po_rate(frm) {
                pepl_recalculate_po_schedule(frm);
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



// PEPL_TENDER_BID_READINESS_PANEL
frappe.ui.form.on("PEPL Tender", {
    refresh(frm) {
        pepl_render_tender_bid_readiness(frm);
    }
});


function pepl_render_tender_bid_readiness(frm) {
    const documents = frm.doc.bid_documents || [];
    const items = frm.doc.items || [];

    const mandatory = documents.filter(
        row => cint(row.is_mandatory) === 1
    );

    const attached = mandatory.filter(
        row => cint(row.is_attached) === 1
    );

    const missing = mandatory.filter(
        row => cint(row.is_attached) !== 1
    );

    const decision_is_bid =
        frm.doc.bid_decision === "Bid";

    const deadline = frm.doc.decision_date;
    let deadline_days = null;
    let deadline_blocked = false;

    if (deadline) {
        deadline_days = frappe.datetime.get_day_diff(
            deadline,
            frappe.datetime.get_today()
        );

        deadline_blocked = deadline_days < 0;
    }

    const has_items = items.length > 0;

    const documents_ready =
        mandatory.length > 0
        && missing.length === 0;

    const approval_required =
        ["Railways", "Defence"].includes(
            frm.doc.sector
        );

    const approval_issues = approval_required
        ? items.filter(row =>
            !["Active", "No Expiry Set"].includes(
                row.vendor_approval_health || "Missing"
            )
        )
        : [];

    const approvals_ready =
        !approval_required
        || (
            items.length > 0
            && approval_issues.length === 0
        );

    const ready =
        decision_is_bid
        && has_items
        && documents_ready
        && approvals_ready
        && !deadline_blocked;

    frm.dashboard.add_indicator(
        __("Bid Readiness: {0}", [
            ready
                ? __("READY")
                : __("NOT READY")
        ]),
        ready ? "green" : "red"
    );

    frm.dashboard.add_indicator(
        __("Mandatory Documents: {0}/{1}", [
            attached.length,
            mandatory.length
        ]),
        documents_ready ? "green" : "orange"
    );

    frm.dashboard.add_indicator(
        __("Tender Items: {0}", [
            items.length
        ]),
        has_items ? "green" : "red"
    );

    if (approval_required) {
        frm.dashboard.add_indicator(
            __("Healthy Vendor Approvals: {0}/{1}", [
                items.length - approval_issues.length,
                items.length
            ]),
            approvals_ready ? "green" : "orange"
        );
    } else {
        frm.dashboard.add_indicator(
            __("Vendor Approval: Not Applicable"),
            "blue"
        );
    }

    if (deadline_days !== null) {
        frm.dashboard.add_indicator(
            deadline_days < 0
                ? __(
                    "Decision Date Overdue by {0} Day(s)",
                    [Math.abs(deadline_days)]
                )
                : __(
                    "Decision Date in {0} Day(s)",
                    [deadline_days]
                ),
            deadline_days < 0
                ? "red"
                : deadline_days <= 3
                    ? "orange"
                    : "blue"
        );
    }

    const blockers = [];

    if (!decision_is_bid) {
        blockers.push(
            __("Bid Decision is not set to Bid.")
        );
    }

    if (!has_items) {
        blockers.push(
            __("No Tender Items are available.")
        );
    }

    if (!mandatory.length) {
        blockers.push(
            __("No mandatory Bid Documents are defined.")
        );
    }

    if (!approvals_ready) {
        const approval_details = approval_issues.map(
            row => {
                const item =
                    row.item
                    || __("Unnamed Item");

                const stage =
                    row.vendor_approval_stage
                    || __("No Record");

                const health =
                    row.vendor_approval_health
                    || __("Missing");

                return (
                    item
                    + " — "
                    + stage
                    + " — "
                    + health
                );
            }
        );

        blockers.push(
            __(
                "Vendor Approval attention required: {0}",
                [approval_details.join(", ")]
            )
        );
    }

    if (missing.length) {
        const missing_names = missing.map(
            row =>
                row.document_type
                || row.document_name
                || __("Unnamed Document")
        );

        blockers.push(
            __(
                "Missing mandatory documents: {0}",
                [missing_names.join(", ")]
            )
        );
    }

    if (deadline_blocked) {
        blockers.push(
            __("Tender decision date has passed.")
        );
    }

    if (blockers.length) {
        frm.dashboard.add_comment(
            blockers.join("<br>"),
            "red",
            true
        );
    } else {
        frm.dashboard.add_comment(
            __(
                "Tender has items, all mandatory Bid Documents "
                + "are attached, and no readiness blocker remains."
            ),
            "green",
            true
        );
    }
}


// PEPL TENDER AUTOMATIC READING / EDITABLE WORD WORKFLOW
frappe.ui.form.on("PEPL Tender", {
    refresh(frm) {
        pepl_add_tender_ingestion_actions(frm);
        pepl_render_tender_ingestion_status(frm);
    }
});


function pepl_add_tender_ingestion_actions(frm) {
    if (frm.is_new()) {
        return;
    }

    if (
        frm.doc.docstatus === 0
        && frm.doc.tender_source_pdf
    ) {
        frm.add_custom_button(
            __("Read Tender PDF"),
            function () {
                frappe.call({
                    method: "pepl_sales.pepl_sales.api.tender_ingestion.read_tender_pdf",
                    args: {
                        tender_name: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __("Reading Tender PDF..."),
                    callback(r) {
                        const result = r.message || {};

                        frappe.msgprint({
                            title: __("Tender Reading Completed"),
                            indicator: (
                                result.warning_count
                                    ? "orange"
                                    : "green"
                            ),
                            message: __(
                                "Pages read: {0}<br>"
                                + "Hyperlinks discovered: {1}<br>"
                                + "Warnings: {2}<br><br>"
                                + "Review the extracted fields against "
                                + "the original Tender before proceeding.",
                                [
                                    result.page_count || 0,
                                    result.link_count || 0,
                                    result.warning_count || 0
                                ]
                            )
                        });

                        frm.reload_doc();
                    }
                });
            },
            __("Tender Automation")
        );
    }

    if (
        frm.doc.docstatus === 0
        && (frm.doc.tender_source_links || []).some(
            row =>
                row.link_type === "GeM Document"
                && !row.downloaded_file
        )
    ) {
        frm.add_custom_button(
            __("Download GeM Tender Documents"),
            function () {
                frappe.call({
                    method: "pepl_sales.pepl_sales.api.tender_ingestion.download_discovered_gem_documents",
                    args: {
                        tender_name: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __(
                        "Retrieving approved GeM tender documents..."
                    ),
                    callback(r) {
                        const result = r.message || {};

                        frappe.msgprint({
                            title: __("GeM Document Retrieval"),
                            indicator: (
                                result.failed
                                    ? "orange"
                                    : "green"
                            ),
                            message: __(
                                "Downloaded: {0}<br>"
                                + "Failed: {1}<br>"
                                + "Skipped: {2}",
                                [
                                    result.downloaded || 0,
                                    result.failed || 0,
                                    result.skipped || 0
                                ]
                            )
                        });

                        frm.reload_doc();
                    }
                });
            },
            __("Tender Automation")
        );
    }

    if (
        frm.doc.docstatus === 0
        && (frm.doc.tender_source_links || []).some(
            row => row.downloaded_file
        )
    ) {
        frm.add_custom_button(
            __("Read Supporting Tender Documents"),
            function () {
                frappe.call({
                    method: "pepl_sales.pepl_sales.api.tender_ingestion.read_supporting_tender_documents",
                    args: {
                        tender_name: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __(
                        "Reading supporting Tender documents..."
                    ),
                    callback(r) {
                        const result = r.message || {};

                        frappe.msgprint({
                            title: __(
                                "Supporting Document Reading Completed"
                            ),
                            indicator: (
                                result.failed
                                    ? "orange"
                                    : "green"
                            ),
                            message: __(
                                "Read successfully: {0}<br>"
                                + "Read with warnings: {1}<br>"
                                + "Manual review: {2}<br>"
                                + "Failed: {3}<br>"
                                + "Skipped: {4}",
                                [
                                    result.read || 0,
                                    result.warnings || 0,
                                    result.manual_review || 0,
                                    result.failed || 0,
                                    result.skipped || 0
                                ]
                            )
                        });

                        frm.reload_doc();
                    }
                });
            },
            __("Tender Automation")
        );
    }

    if (
        frm.doc.docstatus === 0
        && [
            "Read - Review Required",
            "Read with Warnings"
        ].includes(
            frm.doc.tender_ingestion_status
        )
    ) {
        frm.add_custom_button(
            __("Mark Extraction Reviewed"),
            function () {
                frappe.confirm(
                    __(
                        "Confirm that you have compared the extracted "
                        + "information with the original Tender PDF."
                    ),
                    function () {
                        frappe.call({
                            method: "pepl_sales.pepl_sales.api.tender_ingestion.mark_tender_extraction_reviewed",
                            args: {
                                tender_name: frm.doc.name
                            },
                            callback() {
                                frappe.show_alert({
                                    message: __(
                                        "Tender extraction marked Reviewed."
                                    ),
                                    indicator: "green"
                                });

                                frm.reload_doc();
                            }
                        });
                    }
                );
            },
            __("Tender Automation")
        );
    }

    if (
        frm.doc.docstatus === 0
        && frm.doc.tender_ingestion_status
            === "Reviewed"
    ) {
        frm.add_custom_button(
            __("Apply Reviewed Extraction"),
            function () {
                frappe.call({
                    method: "pepl_sales.pepl_sales.api.tender_ingestion.get_reviewed_tender_extraction_preview",
                    args: {
                        tender_name: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __(
                        "Preparing reviewed extraction preview..."
                    ),
                    callback(r) {
                        const data = r.message || {};
                        const current = data.current || {};
                        const extracted = data.extracted || {};

                        const value = function (v) {
                            if (
                                v === null
                                || v === undefined
                                || v === ""
                            ) {
                                return "-";
                            }

                            return frappe.utils.escape_html(
                                String(v)
                            );
                        };

                        const message = [
                            "<b>",
                            __("The following reviewed values will be applied to the ERP Tender:"),
                            "</b><br><br>",

                            __("Publication Date"),
                            ": ",
                            value(current.publication_date),
                            " &rarr; ",
                            value(extracted.publication_date),
                            "<br>",

                            __("Bid Submission Deadline"),
                            ": ",
                            value(current.bid_submission_deadline),
                            " &rarr; ",
                            value(extracted.bid_submission_deadline),
                            "<br>",

                            __("Bid Opening"),
                            ": ",
                            value(current.bid_opening_date),
                            " &rarr; ",
                            value(extracted.bid_opening_date),
                            "<br>",

                            __("EMD Required"),
                            ": ",
                            value(current.emd_required),
                            " &rarr; ",
                            value(extracted.emd_required),
                            "<br>",

                            __("EMD Amount"),
                            ": ",
                            value(current.emd_amount),
                            " &rarr; ",
                            value(extracted.emd_amount),
                            "<br>",

                            __("Splitting Applicable"),
                            ": ",
                            value(current.splitting_applicable),
                            " &rarr; ",
                            value(extracted.splitting_applicable),
                            "<br>",

                            __("Extracted Split Ratio"),
                            ": ",
                            value(extracted.splitting_ratio),
                            "<br><br>",

                            __(
                                "Customer, Sector, Item and other master-linked fields will not be changed."
                            )
                        ].join("");

                        frappe.confirm(
                            message,
                            function () {
                                frappe.call({
                                    method: "pepl_sales.pepl_sales.api.tender_ingestion.apply_reviewed_tender_extraction",
                                    args: {
                                        tender_name: frm.doc.name
                                    },
                                    freeze: true,
                                    freeze_message: __(
                                        "Applying reviewed Tender values..."
                                    ),
                                    callback(apply_r) {
                                        const result =
                                            apply_r.message || {};

                                        frappe.msgprint({
                                            title: __(
                                                "Reviewed Extraction Applied"
                                            ),
                                            indicator: "green",
                                            message: __(
                                                "Reviewed deterministic Tender values were synchronized to ERPNext."
                                            )
                                        });

                                        frm.reload_doc();
                                    }
                                });
                            }
                        );
                    }
                });
            },
            __("Tender Automation")
        );
    }

    if (
        frm.doc.tender_ingestion_status
        === "Reviewed"
    ) {
        frm.add_custom_button(
            __("Generate Editable Word"),
            function () {
                frappe.call({
                    method: "pepl_sales.pepl_sales.api.tender_ingestion.generate_tender_word",
                    args: {
                        tender_name: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __(
                        "Generating editable Tender Word document..."
                    ),
                    callback(r) {
                        const result = r.message || {};

                        if (!result.file_url) {
                            frappe.msgprint(
                                __("Word document could not be generated.")
                            );
                            return;
                        }

                        frappe.show_alert({
                            message: __(
                                "Editable Tender Word generated successfully."
                            ),
                            indicator: "green"
                        });

                        window.open(
                            result.file_url,
                            "_blank"
                        );

                        frm.reload_doc();
                    }
                });
            },
            __("Tender Automation")
        );
    }

    if (frm.doc.generated_tender_word) {
        frm.add_custom_button(
            __("Open Generated Word"),
            function () {
                window.open(
                    frm.doc.generated_tender_word,
                    "_blank"
                );
            },
            __("Tender Automation")
        );
    }
}


function pepl_render_tender_ingestion_status(frm) {
    if (!frm.doc.tender_source_pdf) {
        return;
    }

    const status =
        frm.doc.tender_ingestion_status
        || "Not Read";

    const colors = {
        "Not Read": "grey",
        "Read - Review Required": "orange",
        "Reviewed": "green",
        "Read with Warnings": "orange",
        "Failed": "red"
    };

    frm.dashboard.add_indicator(
        __("Tender Reading: {0}", [status]),
        colors[status] || "grey"
    );

    if (frm.doc.tender_ingestion_warnings) {
        frm.dashboard.add_comment(
            __(
                "Automatic Tender reading requires review: {0}",
                [frm.doc.tender_ingestion_warnings]
            ),
            "orange",
            true
        );
    }
}
