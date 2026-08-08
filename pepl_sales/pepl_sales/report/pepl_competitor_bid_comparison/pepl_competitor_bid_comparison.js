/**
 * PEPL Competitor Bid Comparison — Enhanced Report JS
 * ─────────────────────────────────────────────────────
 * Frappe Script Report · PEPL Sales Module
 *
 * Features:
 *   ① Smart date presets  (Month / Quarter / FY)
 *   ② Column formatters   (badges, icons, numeric styling)
 *   ③ Embedded bar chart  (top-8 competitors: bids vs wins)
 *   ④ Row entrance animation
 *   ⑤ Summary-card hover effect
 *   ⑥ Monospace numeric display
 *   ⑦ Frappe v15-compatible preset mounting
 */

frappe.query_reports["PEPL Competitor Bid Comparison"] = {

	/* ═══════════════════════════════════════════════════════════
	   1 ▸ FILTERS
	═══════════════════════════════════════════════════════════ */
	filters: [
		{
			fieldname: "from_date",
			label: __("Outcome From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(
				frappe.datetime.get_today(),
				-3
			)
		},
		{
			fieldname: "to_date",
			label: __("Outcome To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today()
		},
		{
			fieldname: "tender",
			label: __("Tender"),
			fieldtype: "Link",
			options: "PEPL Tender"
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "sector",
			label: __("Sector"),
			fieldtype: "Select",
			options: "\nRailways\nDefence\nPrivate\nOthers"
		},
		{
			fieldname: "item",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item"
		},
		{
			fieldname: "item_outcome",
			label: __("Item Outcome"),
			fieldtype: "Select",
			options: "\nPending\nWon\nPartially Won\nLost\nCancelled"
		},
		{
			fieldname: "competitor",
			label: __("Competitor Contains"),
			fieldtype: "Data"
		},
		{
			fieldname: "is_pepl",
			label: __("Bidder Type"),
			fieldtype: "Select",
			options: "\n1\n0",
			description: __("1 = PEPL only · 0 = competitors only")
		},
		{
			fieldname: "rank",
			label: __("Rank"),
			fieldtype: "Data",
			description: __("Examples: L1, L2, L10")
		},
		{
			fieldname: "winner_only",
			label: __("Winner Only"),
			fieldtype: "Check"
		}
	],

	/* ═══════════════════════════════════════════════════════════
	   2 ▸ CHART
	   Top-8 competitors: total bids vs wins
	═══════════════════════════════════════════════════════════ */
	get_chart_data(columns, result) {
		if (!result || !result.length) {
			return null;
		}

		var stats = {};

		result.forEach(function (row) {
			if (!row.competitor_name || row.is_pepl) {
				return;
			}

			if (!stats[row.competitor_name]) {
				stats[row.competitor_name] = {
					bids: 0,
					wins: 0
				};
			}

			stats[row.competitor_name].bids++;

			if (row.is_winner || row.buyer_selected) {
				stats[row.competitor_name].wins++;
			}
		});

		var top = Object.entries(stats)
			.sort(function (a, b) {
				return b[1].bids - a[1].bids;
			})
			.slice(0, 8);

		if (!top.length) {
			return null;
		}

		var truncate = function (value) {
			if (!value) {
				return "";
			}

			return value.length > 20
				? value.slice(0, 19) + "…"
				: value;
		};

		return {
			data: {
				labels: top.map(function (entry) {
					return truncate(entry[0]);
				}),
				datasets: [
					{
						name: __("Total Bids"),
						values: top.map(function (entry) {
							return entry[1].bids;
						}),
						chartType: "bar"
					},
					{
						name: __("Wins"),
						values: top.map(function (entry) {
							return entry[1].wins;
						}),
						chartType: "bar"
					}
				]
			},
			type: "bar",
			colors: ["#3b82f6", "#22c55e"],
			height: 230,
			axisOptions: {
				xIsSeries: true
			},
			barOptions: {
				spaceRatio: 0.35
			},
			tooltipOptions: {
				formatTooltipY: function (value) {
					return String(value);
				}
			}
		};
	},

	/* ═══════════════════════════════════════════════════════════
	   3 ▸ COLUMN FORMATTER
	═══════════════════════════════════════════════════════════ */
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(
			value,
			row,
			column,
			data
		);

		if (!data) {
			return value;
		}

		/* ── Item Outcome ─────────────────────────────── */
		if (column.fieldname === "item_outcome") {
			var OUTCOME_MAP = {
				"Won": {
					bg: "#dcfce7",
					fg: "#15803d",
					bd: "#86efac",
					icon: "✓"
				},
				"Partially Won": {
					bg: "#fef3c7",
					fg: "#92400e",
					bd: "#fcd34d",
					icon: "◑"
				},
				"Lost": {
					bg: "#fee2e2",
					fg: "#b91c1c",
					bd: "#fca5a5",
					icon: "✗"
				},
				"Pending": {
					bg: "#f1f5f9",
					fg: "#475569",
					bd: "#cbd5e1",
					icon: "⏳"
				},
				"Cancelled": {
					bg: "#ede9fe",
					fg: "#6d28d9",
					bd: "#c4b5fd",
					icon: "⊘"
				}
			};

			var outcomeStyle =
				OUTCOME_MAP[data.item_outcome] ||
				OUTCOME_MAP["Pending"];

			return (
				'<span style="' +
				"display:inline-flex;" +
				"align-items:center;" +
				"gap:4px;" +
				"background:" + outcomeStyle.bg + ";" +
				"color:" + outcomeStyle.fg + ";" +
				"border:1px solid " + outcomeStyle.bd + ";" +
				"padding:2px 10px;" +
				"border-radius:20px;" +
				"font-weight:700;" +
				"font-size:11px;" +
				'white-space:nowrap">' +
				outcomeStyle.icon +
				" " +
				(data.item_outcome || "—") +
				"</span>"
			);
		}

		/* ── Competitor Name ──────────────────────────── */
		if (column.fieldname === "competitor_name") {
			if (data.is_pepl) {
				return (
					'<span style="' +
					"display:inline-flex;" +
					"align-items:center;" +
					"gap:5px;" +
					"font-weight:700;" +
					'color:#1e40af">' +

					'<span style="' +
					"background:#1e4db7;" +
					"color:#fff;" +
					"padding:1px 7px;" +
					"border-radius:4px;" +
					"font-size:10px;" +
					"font-weight:800;" +
					"letter-spacing:.6px;" +
					'line-height:1.7">PEPL</span>' +

					(data.competitor_name || "") +
					"</span>"
				);
			}

			return (
				'<span style="font-weight:500">' +
				(data.competitor_name || "—") +
				"</span>"
			);
		}

		/* ── Rank ────────────────────────────────────── */
		if (column.fieldname === "rank" && data.rank) {
			var RANK_COLORS = {
				"L1": ["#22c55e", "#fff"],
				"L2": ["#f59e0b", "#fff"],
				"L3": ["#fb923c", "#fff"]
			};

			var rankStyle =
				RANK_COLORS[data.rank] ||
				["#94a3b8", "#fff"];

			return (
				'<span style="' +
				"background:" + rankStyle[0] + ";" +
				"color:" + rankStyle[1] + ";" +
				"padding:2px 10px;" +
				"border-radius:20px;" +
				"font-weight:800;" +
				"font-size:11px;" +
				"box-shadow:0 1px 4px " +
				rankStyle[0] +
				'88">' +
				data.rank +
				"</span>"
			);
		}

		/* ── Sector ──────────────────────────────────── */
		if (column.fieldname === "sector" && data.sector) {
			var SECTOR_COLORS = {
				"Railways": [
					"#eff6ff",
					"#1d4ed8",
					"#93c5fd"
				],
				"Defence": [
					"#fff1f2",
					"#be123c",
					"#fca5a5"
				],
				"Private": [
					"#f5f3ff",
					"#6d28d9",
					"#c4b5fd"
				],
				"Others": [
					"#f8fafc",
					"#475569",
					"#cbd5e1"
				]
			};

			var sectorStyle =
				SECTOR_COLORS[data.sector] ||
				SECTOR_COLORS["Others"];

			return (
				'<span style="' +
				"background:" + sectorStyle[0] + ";" +
				"color:" + sectorStyle[1] + ";" +
				"border:1px solid " + sectorStyle[2] + ";" +
				"padding:2px 9px;" +
				"border-radius:4px;" +
				"font-weight:600;" +
				'font-size:11px">' +
				data.sector +
				"</span>"
			);
		}

		/* ── Percentage Difference ───────────────────── */
		var PERCENT_FIELDS = [
			"difference_from_pepl_percent",
			"difference_from_l1_percent"
		];

		if (
			PERCENT_FIELDS.indexOf(
				column.fieldname
			) !== -1
		) {
			var percentValue = parseFloat(
				data[column.fieldname]
			);

			if (
				isNaN(percentValue) ||
				percentValue === 0
			) {
				return (
					'<span style="color:#94a3b8">—</span>'
				);
			}

			var percentColor =
				percentValue < 0
					? "#15803d"
					: "#b91c1c";

			var arrow =
				percentValue < 0
					? "▼"
					: "▲";

			return (
				'<span style="' +
				"color:" + percentColor + ";" +
				"font-weight:700;" +
				"font-family:'JetBrains Mono'," +
				"'Fira Code',monospace;" +
				'font-size:12px">' +
				arrow +
				" " +
				Math.abs(percentValue).toFixed(2) +
				"%</span>"
			);
		}

		/* ── Boolean Indicators ──────────────────────── */
		if (column.fieldname === "is_winner") {
			return data.is_winner
				? '<span style="font-size:14px" title="Winner">🏆</span>'
				: "";
		}

		if (column.fieldname === "is_l1") {
			return data.is_l1
				? '<span style="color:#15803d;font-size:15px;font-weight:900" title="L1 – Lowest Bidder">✓</span>'
				: "";
		}

		if (column.fieldname === "buyer_selected") {
			return data.buyer_selected
				? '<span style="color:#1d4ed8;font-size:14px" title="Buyer Selected">★</span>'
				: "";
		}

		if (column.fieldname === "is_pepl") {
			return data.is_pepl
				? '<span style="color:#1e4db7;font-size:14px">●</span>'
				: '<span style="color:#cbd5e1">○</span>';
		}

		if (column.fieldname === "is_msme") {
			return data.is_msme
				? (
					'<span style="' +
					"background:#fffbeb;" +
					"color:#92400e;" +
					"padding:1px 7px;" +
					"border-radius:4px;" +
					"font-size:10px;" +
					"font-weight:700;" +
					'border:1px solid #fcd34d">MSME</span>'
				)
				: "";
		}

		if (column.fieldname === "is_mii") {
			return data.is_mii
				? (
					'<span style="' +
					"background:#eff6ff;" +
					"color:#1e40af;" +
					"padding:1px 7px;" +
					"border-radius:4px;" +
					"font-size:10px;" +
					"font-weight:700;" +
					'border:1px solid #93c5fd">MII</span>'
				)
				: "";
		}

		return value;
	},

	/* ═══════════════════════════════════════════════════════════
	   4 ▸ ON LOAD
	═══════════════════════════════════════════════════════════ */
	onload(report) {
		_peplInjectStyles();

		/*
		 * Frappe v15 may mount the report filter DOM slightly
		 * after onload. Try more than once safely.
		 */
		setTimeout(function () {
			_peplMountPresets(report);
		}, 250);

		setTimeout(function () {
			_peplMountPresets(report);
		}, 750);

		setTimeout(function () {
			_peplMountPresets(report);
		}, 1500);
	},

	/* ═══════════════════════════════════════════════════════════
	   5 ▸ AFTER RENDER
	═══════════════════════════════════════════════════════════ */
	after_render() {
		document
			.querySelectorAll(".dt-body .dt-row")
			.forEach(function (row, index) {
				row.style.animationDelay =
					(index * 18) + "ms";
			});
	}
};


/* ═══════════════════════════════════════════════════════════════
   PRIVATE HELPERS
═══════════════════════════════════════════════════════════════ */

/**
 * Inject custom report stylesheet once.
 */
function _peplInjectStyles() {
	if (
		document.getElementById(
			"pepl-bid-cmp-styles"
		)
	) {
		return;
	}

	var style = document.createElement("style");
	style.id = "pepl-bid-cmp-styles";

	style.textContent = [
		/* DataTable */
		".dt-cell__content {",
		"  transition: background .15s ease !important;",
		"}",

		".dt-row:hover .dt-cell__content {",
		"  background: rgba(30,77,183,.055) !important;",
		"}",

		/* Summary cards */
		".report-summary-wrapper .summary-card,",
		".report-summary .summary-card,",
		".report-summary-wrapper .summary-item,",
		".report-summary .summary-item {",
		"  transition:",
		"    transform .22s cubic-bezier(.34,1.56,.64,1),",
		"    box-shadow .22s ease !important;",
		"  cursor: default;",
		"}",

		".report-summary-wrapper .summary-card:hover,",
		".report-summary .summary-card:hover,",
		".report-summary-wrapper .summary-item:hover,",
		".report-summary .summary-item:hover {",
		"  transform: translateY(-4px) scale(1.025) !important;",
		"  box-shadow: 0 14px 32px rgba(30,77,183,.16) !important;",
		"}",

		/* Quick-filter preset bar */
		"#_pepl-presets {",
		"  display: flex;",
		"  align-items: center;",
		"  gap: 6px;",
		"  flex-wrap: wrap;",
		"  padding: 9px 12px;",
		"  margin: 0 0 10px 0;",
		"  background: linear-gradient(135deg,#f0f4ff,#e8f0fe);",
		"  border: 1px solid #c7d7fb;",
		"  border-radius: 10px;",
		"  width: 100%;",
		"}",

		"#_pepl-presets .pp-lbl {",
		"  font-size: 11px;",
		"  font-weight: 700;",
		"  color: #374151;",
		"  letter-spacing: .5px;",
		"  text-transform: uppercase;",
		"  margin-right: 4px;",
		"}",

		".pp-btn {",
		"  background: #fff;",
		"  border: 1.5px solid #c7d7fb;",
		"  border-radius: 20px;",
		"  padding: 4px 14px;",
		"  font-size: 11px;",
		"  font-weight: 600;",
		"  color: #1e4db7;",
		"  cursor: pointer;",
		"  transition: all .18s cubic-bezier(.34,1.56,.64,1);",
		"  outline: none;",
		"}",

		".pp-btn:hover,",
		".pp-btn.active {",
		"  background: #1e4db7;",
		"  color: #fff;",
		"  border-color: #1e4db7;",
		"  transform: translateY(-1px);",
		"  box-shadow: 0 4px 12px rgba(30,77,183,.28);",
		"}",

		".pp-btn-clear {",
		"  background: #fee2e2 !important;",
		"  border-color: #fca5a5 !important;",
		"  color: #dc2626 !important;",
		"}",

		".pp-btn-clear:hover,",
		".pp-btn-clear.active {",
		"  background: #dc2626 !important;",
		"  color: #fff !important;",
		"  border-color: #dc2626 !important;",
		"}",

		/* Row animation */
		"@keyframes _ppRowIn {",
		"  from {",
		"    opacity: 0;",
		"    transform: translateX(-8px);",
		"  }",
		"  to {",
		"    opacity: 1;",
		"    transform: none;",
		"  }",
		"}",

		".dt-body .dt-row {",
		"  animation: _ppRowIn .28s ease both;",
		"}",

		/* Numeric fields */
		"[data-fieldtype='Currency'] .dt-cell__content,",
		"[data-fieldtype='Percent'] .dt-cell__content,",
		"[data-fieldtype='Float'] .dt-cell__content,",
		"[data-fieldtype='Int'] .dt-cell__content {",
		"  font-family:",
		"    'JetBrains Mono',",
		"    'Fira Code',",
		"    monospace !important;",
		"  font-size: 12px;",
		"}"
	].join("\n");

	document.head.appendChild(style);
}


/**
 * Find the correct Frappe report filter/form container.
 */
function _peplFindFilterContainer(report) {
	if (!report) {
		return null;
	}

	/*
	 * Prefer Frappe's actual page-form jQuery object.
	 */
	if (
		report.page &&
		report.page.page_form &&
		report.page.page_form.length
	) {
		return report.page.page_form[0];
	}

	var root =
		report.page &&
		report.page.wrapper
			? report.page.wrapper
			: document;

	/*
	 * Compatibility fallbacks for various Frappe v15 builds.
	 */
	var selectors = [
		".page-form",
		".filter-area",
		".report-filters",
		".standard-filter-section",
		".filter-section"
	];

	for (
		var index = 0;
		index < selectors.length;
		index++
	) {
		var element =
			root.querySelector(
				selectors[index]
			);

		if (element) {
			return element;
		}
	}

	return null;
}


/**
 * Mount quick-date preset bar.
 */
function _peplMountPresets(report) {
	if (
		document.getElementById(
			"_pepl-presets"
		)
	) {
		return;
	}

	var wrap =
		_peplFindFilterContainer(report);

	if (!wrap) {
		console.warn(
			"[PEPL Competitor Bid Comparison] " +
			"Could not find report filter container."
		);
		return;
	}

	var presets = [
		"This Month",
		"Last Month",
		"This Quarter",
		"Last Quarter",
		"This FY",
		"Last FY"
	];

	var buttonHtml =
		presets
			.map(function (label) {
				return (
					'<button type="button" ' +
					'class="pp-btn" ' +
					'data-key="' +
					label +
					'">' +
					label +
					"</button>"
				);
			})
			.join("");

	buttonHtml +=
		'<button type="button" ' +
		'class="pp-btn pp-btn-clear" ' +
		'data-key="Clear">' +
		"✕ Clear" +
		"</button>";

	var bar =
		document.createElement("div");

	bar.id = "_pepl-presets";

	bar.innerHTML =
		'<span class="pp-lbl">' +
		"⚡ Quick:" +
		"</span>" +
		buttonHtml;

	/*
	 * Put the quick filter strip above existing
	 * Frappe report filters.
	 */
	if (wrap.firstChild) {
		wrap.insertBefore(
			bar,
			wrap.firstChild
		);
	} else {
		wrap.appendChild(bar);
	}

	bar
		.querySelectorAll(".pp-btn")
		.forEach(function (button) {
			button.addEventListener(
				"click",
				function (event) {
					event.preventDefault();
					event.stopPropagation();

					bar
						.querySelectorAll(
							".pp-btn"
						)
						.forEach(
							function (item) {
								item.classList.remove(
									"active"
								);
							}
						);

					button.classList.add(
						"active"
					);

					_peplApplyPreset(
						button.dataset.key,
						report
					);
				}
			);
		});
}


/**
 * Apply quick date preset and refresh report.
 */
function _peplApplyPreset(key, report) {
	var today =
		frappe.datetime.get_today();

	/*
	 * Use Frappe date rather than browser-local
	 * new Date() as the primary source.
	 */
	var now =
		frappe.datetime.str_to_obj(
			today
		);

	var financialYearStart =
		now.getMonth() >= 3
			? now.getFullYear()
			: now.getFullYear() - 1;

	var toDateString = function (
		dateObject
	) {
		return frappe.datetime.obj_to_str(
			dateObject
		);
	};

	var monthStart = function (
		dateString
	) {
		var date =
			frappe.datetime.str_to_obj(
				dateString
			);

		date.setDate(1);

		return toDateString(date);
	};

	var monthEnd = function (
		dateString
	) {
		var date =
			frappe.datetime.str_to_obj(
				dateString
			);

		date.setMonth(
			date.getMonth() + 1
		);

		date.setDate(0);

		return toDateString(date);
	};

	var fromDate;
	var toDate;

	switch (key) {

		case "This Month":
			fromDate =
				monthStart(today);

			toDate =
				monthEnd(today);
			break;

		case "Last Month": {
			var lastMonth =
				frappe.datetime.add_months(
					today,
					-1
				);

			fromDate =
				monthStart(lastMonth);

			toDate =
				monthEnd(lastMonth);
			break;
		}

		case "This Quarter": {
			var currentQuarter =
				Math.floor(
					now.getMonth() / 3
				);

			fromDate =
				toDateString(
					new Date(
						now.getFullYear(),
						currentQuarter * 3,
						1
					)
				);

			toDate =
				toDateString(
					new Date(
						now.getFullYear(),
						(currentQuarter + 1) * 3,
						0
					)
				);
			break;
		}

		case "Last Quarter": {
			var previousQuarter =
				Math.floor(
					now.getMonth() / 3
				) - 1;

			var previousQuarterYear;
			var adjustedQuarter;

			if (previousQuarter < 0) {
				previousQuarterYear =
					now.getFullYear() - 1;

				adjustedQuarter = 3;
			} else {
				previousQuarterYear =
					now.getFullYear();

				adjustedQuarter =
					previousQuarter;
			}

			fromDate =
				toDateString(
					new Date(
						previousQuarterYear,
						adjustedQuarter * 3,
						1
					)
				);

			toDate =
				toDateString(
					new Date(
						previousQuarterYear,
						(adjustedQuarter + 1) * 3,
						0
					)
				);
			break;
		}

		case "This FY":
			fromDate =
				financialYearStart +
				"-04-01";

			toDate =
				(financialYearStart + 1) +
				"-03-31";
			break;

		case "Last FY":
			fromDate =
				(financialYearStart - 1) +
				"-04-01";

			toDate =
				financialYearStart +
				"-03-31";
			break;

		case "Clear":
			report.set_filter_value(
				"from_date",
				""
			);

			report.set_filter_value(
				"to_date",
				""
			);

			report.refresh();
			return;

		default:
			return;
	}

	report.set_filter_value(
		"from_date",
		fromDate
	);

	report.set_filter_value(
		"to_date",
		toDate
	);

	report.refresh();
}