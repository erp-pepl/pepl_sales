/**
 * PEPL Competitor Bid Comparison
 * ─────────────────────────────────────────────────────────────
 * Frappe Script Report  ·  PEPL Sales Module
 *
 *  ①  Outcome summary cards — count-up animation, click-to-filter,
 *      active ring highlight
 *  ②  Column formatters — outcome badges, rank pills, sector chips,
 *      PEPL tag, percentage arrows, boolean icons
 *  ③  Embedded Frappe bar chart — top-8 competitors: bids vs wins
 *  ④  Quick Analytics dialog — Chart.js doughnut + bar
 *  ⑤  Clear Filters inner button
 *  ⑥  Row entrance animation
 *  ⑦  Monospace numeric columns
 */

frappe.query_reports["PEPL Competitor Bid Comparison"] = {

	/* ═══════════════════════════════════════════════════════════
	   FILTERS
	═══════════════════════════════════════════════════════════ */
	filters: [
		{
			fieldname : "from_date",
			label     : __("Outcome From Date"),
			fieldtype : "Date",
			default   : frappe.datetime.add_months(
				frappe.datetime.get_today(), -3
			)
		},
		{
			fieldname : "to_date",
			label     : __("Outcome To Date"),
			fieldtype : "Date",
			default   : frappe.datetime.get_today()
		},
		{
			fieldname : "tender",
			label     : __("Tender"),
			fieldtype : "Link",
			options   : "PEPL Tender"
		},
		{
			fieldname : "customer",
			label     : __("Customer"),
			fieldtype : "Link",
			options   : "Customer"
		},
		{
			fieldname : "sector",
			label     : __("Sector"),
			fieldtype : "Select",
			options   : "\nRailways\nDefence\nPrivate\nOthers"
		},
		{
			fieldname : "item",
			label     : __("Item"),
			fieldtype : "Link",
			options   : "Item"
		},
		{
			fieldname : "item_outcome",
			label     : __("Item Outcome"),
			fieldtype : "Select",
			options   : "\nPending\nWon\nPartially Won\nLost\nCancelled"
		},
		{
			fieldname    : "competitor",
			label        : __("Competitor Contains"),
			fieldtype    : "Data"
		},
		{
			fieldname    : "is_pepl",
			label        : __("Bidder Type"),
			fieldtype    : "Select",
			options      : "\n1\n0",
			description  : __("1 = PEPL only  ·  0 = Competitors only")
		},
		{
			fieldname    : "rank",
			label        : __("Rank"),
			fieldtype    : "Data",
			description  : __("E.g. L1, L2, L10")
		},
		{
			fieldname : "winner_only",
			label     : __("Winner Only"),
			fieldtype : "Check"
		}
	],


	/* ═══════════════════════════════════════════════════════════
	   FRAPPE CHART  —  top-8 competitors: total bids vs wins
	═══════════════════════════════════════════════════════════ */
	get_chart_data(columns, result) {
		if (!result || !result.length) return null;

		const stats = {};

		result.forEach(function (row) {
			if (!row.competitor_name || row.is_pepl) return;

			if (!stats[row.competitor_name]) {
				stats[row.competitor_name] = { bids: 0, wins: 0 };
			}

			stats[row.competitor_name].bids++;

			if (row.is_winner || row.buyer_selected) {
				stats[row.competitor_name].wins++;
			}
		});

		const top = Object.entries(stats)
			.sort((a, b) => b[1].bids - a[1].bids)
			.slice(0, 8);

		if (!top.length) return null;

		const trim = (s) =>
			s && s.length > 20 ? s.slice(0, 19) + "…" : (s || "");

		return {
			data: {
				labels   : top.map((e) => trim(e[0])),
				datasets : [
					{
						name      : __("Total Bids"),
						values    : top.map((e) => e[1].bids),
						chartType : "bar"
					},
					{
						name      : __("Wins"),
						values    : top.map((e) => e[1].wins),
						chartType : "bar"
					}
				]
			},
			type          : "bar",
			colors        : ["#3b82f6", "#22c55e"],
			height        : 240,
			axisOptions   : { xIsSeries: true },
			barOptions    : { spaceRatio: 0.35 },
			tooltipOptions: {
				formatTooltipY: (v) => String(v)
			}
		};
	},


	/* ═══════════════════════════════════════════════════════════
	   COLUMN FORMATTER
	═══════════════════════════════════════════════════════════ */
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		/* ─── Item Outcome badge ─────────────────────────────── */
		if (column.fieldname === "item_outcome") {
			const MAP = {
				"Won"          : { bg:"#dcfce7", fg:"#15803d", bd:"#86efac", icon:"✓" },
				"Partially Won": { bg:"#fef3c7", fg:"#92400e", bd:"#fcd34d", icon:"◑" },
				"Lost"         : { bg:"#fee2e2", fg:"#b91c1c", bd:"#fca5a5", icon:"✗" },
				"Pending"      : { bg:"#f1f5f9", fg:"#475569", bd:"#cbd5e1", icon:"⏳" },
				"Cancelled"    : { bg:"#ede9fe", fg:"#6d28d9", bd:"#c4b5fd", icon:"⊘" }
			};
			const s = MAP[data.item_outcome] || MAP["Pending"];
			return (
				`<span style="display:inline-flex;align-items:center;gap:4px;`+
				`background:${s.bg};color:${s.fg};border:1px solid ${s.bd};`+
				`padding:2px 10px;border-radius:20px;font-weight:700;font-size:11px;white-space:nowrap">` +
				`${s.icon} ${data.item_outcome || "—"}</span>`
			);
		}

		/* ─── Competitor Name — PEPL tag ─────────────────────── */
		if (column.fieldname === "competitor_name") {
			if (data.is_pepl) {
				return (
					`<span style="display:inline-flex;align-items:center;gap:5px;`+
					`font-weight:700;color:#1e40af">` +
					`<span style="background:#1e4db7;color:#fff;padding:1px 7px;`+
					`border-radius:4px;font-size:10px;font-weight:800;`+
					`letter-spacing:.6px;line-height:1.7">PEPL</span>` +
					`${data.competitor_name || ""}</span>`
				);
			}
			return `<span style="font-weight:500">${data.competitor_name || "—"}</span>`;
		}

		/* ─── Rank pill ──────────────────────────────────────── */
		if (column.fieldname === "rank" && data.rank) {
			const RC = {
				"L1": ["#22c55e","#fff"],
				"L2": ["#f59e0b","#fff"],
				"L3": ["#fb923c","#fff"]
			};
			const c = RC[data.rank] || ["#94a3b8","#fff"];
			return (
				`<span style="background:${c[0]};color:${c[1]};`+
				`padding:2px 10px;border-radius:20px;font-weight:800;`+
				`font-size:11px;box-shadow:0 1px 4px ${c[0]}88">` +
				`${data.rank}</span>`
			);
		}

		/* ─── Sector chip ────────────────────────────────────── */
		if (column.fieldname === "sector" && data.sector) {
			const SC = {
				"Railways": ["#eff6ff","#1d4ed8","#93c5fd"],
				"Defence" : ["#fff1f2","#be123c","#fca5a5"],
				"Private" : ["#f5f3ff","#6d28d9","#c4b5fd"],
				"Others"  : ["#f8fafc","#475569","#cbd5e1"]
			};
			const s = SC[data.sector] || SC["Others"];
			return (
				`<span style="background:${s[0]};color:${s[1]};`+
				`border:1px solid ${s[2]};padding:2px 9px;`+
				`border-radius:4px;font-weight:600;font-size:11px">` +
				`${data.sector}</span>`
			);
		}

		/* ─── Percentage difference fields ───────────────────── */
		const PCT_FIELDS = [
			"difference_from_pepl_percent",
			"difference_from_l1_percent"
		];
		if (PCT_FIELDS.includes(column.fieldname)) {
			const pv = parseFloat(data[column.fieldname]);
			if (isNaN(pv) || pv === 0) {
				return `<span style="color:#94a3b8">—</span>`;
			}
			const color  = pv < 0 ? "#15803d" : "#b91c1c";
			const arrow  = pv < 0 ? "▼" : "▲";
			return (
				`<span style="color:${color};font-weight:700;`+
				`font-family:'JetBrains Mono','Fira Code',monospace;font-size:12px">` +
				`${arrow} ${Math.abs(pv).toFixed(2)}%</span>`
			);
		}

		/* ─── Boolean / icon columns ─────────────────────────── */
		if (column.fieldname === "is_winner") {
			return data.is_winner
				? `<span style="font-size:14px" title="Winner">🏆</span>` : "";
		}
		if (column.fieldname === "is_l1") {
			return data.is_l1
				? `<span style="color:#15803d;font-size:15px;font-weight:900" title="L1">✓</span>` : "";
		}
		if (column.fieldname === "buyer_selected") {
			return data.buyer_selected
				? `<span style="color:#1d4ed8;font-size:14px" title="Buyer Selected">★</span>` : "";
		}
		if (column.fieldname === "is_pepl") {
			return data.is_pepl
				? `<span style="color:#1e4db7;font-size:14px">●</span>`
				: `<span style="color:#cbd5e1">○</span>`;
		}
		if (column.fieldname === "is_msme") {
			return data.is_msme
				? `<span style="background:#fffbeb;color:#92400e;padding:1px 7px;`+
				  `border-radius:4px;font-size:10px;font-weight:700;border:1px solid #fcd34d">MSME</span>`
				: "";
		}
		if (column.fieldname === "is_mii") {
			return data.is_mii
				? `<span style="background:#eff6ff;color:#1e40af;padding:1px 7px;`+
				  `border-radius:4px;font-size:10px;font-weight:700;border:1px solid #93c5fd">MII</span>`
				: "";
		}

		return value;
	},


	/* ═══════════════════════════════════════════════════════════
	   ON LOAD
	═══════════════════════════════════════════════════════════ */
	onload(report) {
		_bcInjectStyles();
		_bcInitSummaryCards(report);

		/* ── Clear Filters button ──────────────────────────── */
		report.page.add_inner_button(__("Clear Filters"), function () {
			[
				"from_date","to_date","tender","customer","sector",
				"item","item_outcome","competitor","is_pepl","rank","winner_only"
			].forEach((f) => report.set_filter_value(f, ""));

			/* Remove active highlight from all cards */
			document
				.querySelectorAll(".bc-summary-card.bc-card-active")
				.forEach((c) => c.classList.remove("bc-card-active"));

			report.refresh();
		});

		/* ── Quick Analytics button ────────────────────────── */
		report.page.add_inner_button(__("Quick Analytics"), function () {
			_bcOpenAnalyticsDialog();
		});
	},


	/* ═══════════════════════════════════════════════════════════
	   AFTER RENDER
	═══════════════════════════════════════════════════════════ */
	after_render() {
		/* Row entrance animation */
		document.querySelectorAll(".dt-body .dt-row").forEach((row, i) => {
			row.style.animationDelay = (i * 18) + "ms";
		});

		/* Redraw summary cards with fresh row data */
		setTimeout(() => _bcDrawSummaryCards(frappe.query_report), 150);
	}
};


/* ═══════════════════════════════════════════════════════════════
   ▸ PRIVATE HELPERS
═══════════════════════════════════════════════════════════════ */

/* ── Safely retrieve current report rows ─────────────────────── */
function _bcGetRows(report) {
	if (report && Array.isArray(report.data)) return report.data;
	if (frappe.query_report && Array.isArray(frappe.query_report.data)) {
		return frappe.query_report.data;
	}
	return [];
}


/* ─────────────────────────────────────────────────────────────
   SUMMARY CARDS
   8 cards in a 4-column grid, styled after the Appointment
   report: white card, coloured top-accent bar, large bold
   count with count-up animation, hover lift, click-to-filter.
───────────────────────────────────────────────────────────── */

function _bcInitSummaryCards(report) {
	_bcEnsureSummaryWrapper(report);

	/* Poll until first data load populates report.data */
	let attempts = 0;
	const poll = setInterval(function () {
		attempts++;
		const rows = _bcGetRows(frappe.query_report);
		if (rows.length > 0 || attempts > 30) {
			clearInterval(poll);
			_bcDrawSummaryCards(frappe.query_report);
		}
	}, 200);
}


function _bcEnsureSummaryWrapper(report) {
	if (document.getElementById("bc-summary-wrap")) {
		return document.getElementById("bc-summary-wrap");
	}

	const wrap = document.createElement("div");
	wrap.id = "bc-summary-wrap";

	try {
		const form = report.page.main.find(".frappe-form")[0];
		if (form) {
			form.parentNode.insertBefore(wrap, form.nextSibling);
		} else {
			const body = report.page.main[0];
			if (body) body.insertBefore(wrap, body.firstChild);
		}
	} catch (_) {
		document.body.appendChild(wrap);
	}

	return wrap;
}


function _bcDrawSummaryCards(report) {
	let wrap = document.getElementById("bc-summary-wrap");
	if (!wrap) {
		wrap = _bcEnsureSummaryWrapper(report || frappe.query_report);
	}
	if (!wrap) return;

	const rows   = _bcGetRows(report || frappe.query_report);
	const counts = _bcCountStats(rows);

	/*
	 * Card definitions.
	 * filter_key / filter_val drive the click-to-filter logic.
	 * Special values "__all__" and "__l1__" are handled manually.
	 */
	const cards = [
		{
			label      : "Total Entries",
			value      : counts.total,
			accent     : "#1e4db7",
			color_cls  : "bc-val-blue",
			filter_key : "__all__",
			filter_val : ""
		},
		{
			label      : "PEPL Bids",
			value      : counts.pepl_bids,
			accent     : "#1e40af",
			color_cls  : "bc-val-navy",
			filter_key : "is_pepl",
			filter_val : "1"
		},
		{
			label      : "Won",
			value      : counts.won,
			accent     : "#15803d",
			color_cls  : "bc-val-green",
			filter_key : "item_outcome",
			filter_val : "Won"
		},
		{
			label      : "Partially Won",
			value      : counts.partially_won,
			accent     : "#92400e",
			color_cls  : "bc-val-amber",
			filter_key : "item_outcome",
			filter_val : "Partially Won"
		},
		{
			label      : "Lost",
			value      : counts.lost,
			accent     : "#b91c1c",
			color_cls  : "bc-val-red",
			filter_key : "item_outcome",
			filter_val : "Lost"
		},
		{
			label      : "Pending",
			value      : counts.pending,
			accent     : "#475569",
			color_cls  : "bc-val-slate",
			filter_key : "item_outcome",
			filter_val : "Pending"
		},
		{
			label      : "Cancelled",
			value      : counts.cancelled,
			accent     : "#6d28d9",
			color_cls  : "bc-val-purple",
			filter_key : "item_outcome",
			filter_val : "Cancelled"
		},
		{
			label      : "L1 Bids",
			value      : counts.l1_bids,
			accent     : "#0f766e",
			color_cls  : "bc-val-teal",
			filter_key : "__l1__",
			filter_val : "L1"
		}
	];

	let html = `<div class="bc-summary-grid">`;

	cards.forEach((card) => {
		html +=
			`<div class="bc-summary-card" ` +
			`data-filter-key="${card.filter_key}" ` +
			`data-filter-val="${card.filter_val}" ` +
			`style="--bc-accent:${card.accent};" ` +
			`title="Click to filter by ${card.label}">` +
			`<div class="bc-card-label">${card.label}</div>` +
			`<div class="bc-card-value ${card.color_cls}" data-target="${card.value}">0</div>` +
			`</div>`;
	});

	html += `</div>`;
	wrap.innerHTML = html;

	/* Count-up animation */
	wrap.querySelectorAll(".bc-card-value[data-target]").forEach((el) => {
		_bcAnimateCount(
			el,
			parseInt(el.getAttribute("data-target"), 10) || 0,
			650
		);
	});

	/* Click-to-filter handler */
	wrap.querySelectorAll(".bc-summary-card").forEach((card) => {
		card.addEventListener("click", function () {
			const key = card.getAttribute("data-filter-key");
			const val = card.getAttribute("data-filter-val");
			const isActive = card.classList.contains("bc-card-active");

			/* Clear active state on all cards */
			wrap.querySelectorAll(".bc-summary-card")
				.forEach((c) => c.classList.remove("bc-card-active"));

			if (isActive) {
				/* Second click → remove filter */
				_bcClearCardFilters();
				return;
			}

			card.classList.add("bc-card-active");
			_bcApplyCardFilter(key, val);
		});
	});
}


function _bcCountStats(rows) {
	const c = {
		total: 0, pepl_bids: 0, won: 0,
		partially_won: 0, lost: 0, pending: 0,
		cancelled: 0, l1_bids: 0
	};

	(rows || []).forEach((row) => {
		if (!row) return;
		c.total++;
		if (row.is_pepl)  c.pepl_bids++;
		if (row.is_l1)    c.l1_bids++;
		switch (row.item_outcome) {
			case "Won"          : c.won++;           break;
			case "Partially Won": c.partially_won++; break;
			case "Lost"         : c.lost++;          break;
			case "Pending"      : c.pending++;       break;
			case "Cancelled"    : c.cancelled++;     break;
		}
	});

	return c;
}


/* Apply filter based on the card's key/val */
function _bcApplyCardFilter(key, val) {
	if (key === "__all__") {
		_bcClearCardFilters();
		return;
	}

	/* Reset conflicting filters first */
	frappe.query_report.set_filter_value("item_outcome", "");
	frappe.query_report.set_filter_value("is_pepl", "");
	frappe.query_report.set_filter_value("rank", "");

	if (key === "__l1__") {
		frappe.query_report.set_filter_value("rank", val);
	} else {
		frappe.query_report.set_filter_value(key, val);
	}

	frappe.query_report.refresh();
}


function _bcClearCardFilters() {
	frappe.query_report.set_filter_value("item_outcome", "");
	frappe.query_report.set_filter_value("is_pepl", "");
	frappe.query_report.set_filter_value("rank", "");
	frappe.query_report.refresh();
}


/* Smooth count-up animation */
function _bcAnimateCount(el, target, duration) {
	if (!el) return;
	const step = Math.max(1, Math.ceil(target / (duration / 30)));
	let current = 0;
	el.textContent = "0";

	const timer = setInterval(() => {
		current += step;
		if (current >= target) {
			el.textContent = target;
			clearInterval(timer);
		} else {
			el.textContent = current;
		}
	}, 30);
}


/* ─────────────────────────────────────────────────────────────
   QUICK ANALYTICS DIALOG
   Chart.js doughnut (outcome split) + bar (top-10 competitors).
   Uses a per-open counter so canvas IDs are always unique,
   preventing Chart.js blank-chart on second open.
───────────────────────────────────────────────────────────── */

let _bcAnalyticsOpenCount = 0;

function _bcLoadChartJs(cb) {
	/* Chart.js v4 exposes .register(); Frappe Charts does not. */
	if (window.Chart && typeof window.Chart.register === "function") {
		return cb();
	}

	const s    = document.createElement("script");
	s.src      = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js";
	s.onload   = cb;
	s.onerror  = () => frappe.msgprint({
		title    : __("Chart.js Load Error"),
		message  : __("Could not load Chart.js from CDN. Check your internet connection."),
		indicator: "red"
	});
	document.head.appendChild(s);
}


function _bcDestroyChart(canvas) {
	if (!canvas) return;
	const existing = Chart.getChart(canvas);
	if (existing)  existing.destroy();
}


function _bcOpenAnalyticsDialog() {
	const rows   = _bcGetRows(frappe.query_report);
	const counts = _bcCountStats(rows);

	_bcAnalyticsOpenCount++;
	const uid        = _bcAnalyticsOpenCount;
	const ID_DONUT   = `bc-donut-${uid}`;
	const ID_BAR_TOP = `bc-bar-top-${uid}`;

	/* ── Top-10 competitors by bid count ─────────────────── */
	const compStats = {};
	(rows || []).forEach((row) => {
		if (!row || !row.competitor_name || row.is_pepl) return;
		if (!compStats[row.competitor_name]) {
			compStats[row.competitor_name] = { bids: 0, wins: 0 };
		}
		compStats[row.competitor_name].bids++;
		if (row.is_winner || row.buyer_selected) {
			compStats[row.competitor_name].wins++;
		}
	});
	const topComps = Object.entries(compStats)
		.sort((a, b) => b[1].bids - a[1].bids)
		.slice(0, 10);

	/* ── Outcome data ────────────────────────────────────── */
	const outcomeLabels = ["Won","Partially Won","Lost","Pending","Cancelled"];
	const outcomeValues = [
		counts.won, counts.partially_won,
		counts.lost, counts.pending, counts.cancelled
	];
	const outcomeBg = ["#22c55e","#f59e0b","#ef4444","#94a3b8","#a78bfa"];

	/* Win rate string */
	const totalDecided = counts.won + counts.partially_won + counts.lost;
	const winRate = totalDecided > 0
		? ((counts.won / totalDecided) * 100).toFixed(1) + "%"
		: "N/A";

	const dialogHtml = `
		<div style="padding:8px 4px 0 4px;">

			<!-- KPI strip -->
			<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;">
				${[
					["Total Entries", counts.total,       "#1e4db7"],
					["PEPL Bids",     counts.pepl_bids,   "#1e40af"],
					["L1 Bids",       counts.l1_bids,     "#0f766e"],
					["Win Rate",      winRate,             "#15803d"]
				].map(([lbl, val, clr]) => `
					<div style="flex:1;min-width:130px;background:#f8fafc;
					            border:1px solid #e2e8f0;border-radius:10px;
					            padding:12px 16px;text-align:center;">
						<div style="font-size:11px;font-weight:700;color:#64748b;
						            text-transform:uppercase;letter-spacing:.5px;
						            margin-bottom:6px;">${lbl}</div>
						<div style="font-size:28px;font-weight:800;color:${clr};">${val}</div>
					</div>
				`).join("")}
			</div>

			<!-- Charts row -->
			<div style="display:flex;gap:20px;flex-wrap:wrap;align-items:flex-start;">

				<!-- Doughnut -->
				<div style="flex:1;min-width:260px;max-width:340px;
				            background:#fafbfc;border:1px solid #e9ecef;
				            border-radius:10px;padding:16px;">
					<div style="font-size:12px;font-weight:700;color:#374151;
					            text-align:center;margin-bottom:12px;
					            text-transform:uppercase;letter-spacing:.4px;">
						Outcome Distribution
					</div>
					<canvas id="${ID_DONUT}" style="max-height:280px;"></canvas>
				</div>

				<!-- Top-10 Competitors bar -->
				<div style="flex:2;min-width:280px;
				            background:#fafbfc;border:1px solid #e9ecef;
				            border-radius:10px;padding:16px;">
					<div style="font-size:12px;font-weight:700;color:#374151;
					            text-align:center;margin-bottom:12px;
					            text-transform:uppercase;letter-spacing:.4px;">
						Top Competitors — Bids vs Wins
					</div>
					<canvas id="${ID_BAR_TOP}" style="max-height:280px;"></canvas>
				</div>

			</div>
		</div>
	`;

	const dlg = new frappe.ui.Dialog({
		title  : __("Bid Comparison Analytics"),
		size   : "extra-large",
		fields : [{ fieldname:"chart_html", fieldtype:"HTML", options: dialogHtml }]
	});

	dlg.show();

	_bcLoadChartJs(function () {
		setTimeout(function () {
			const c1 = document.getElementById(ID_DONUT);
			const c2 = document.getElementById(ID_BAR_TOP);

			if (!c1 || !c2) {
				frappe.msgprint(__("Chart canvases not found — please try reopening."));
				return;
			}

			_bcDestroyChart(c1);
			_bcDestroyChart(c2);

			/* ── Doughnut ─────────────────────────────────── */
			new Chart(c1, {
				type : "doughnut",
				data : {
					labels  : outcomeLabels,
					datasets: [{
						data           : outcomeValues,
						backgroundColor: outcomeBg,
						borderWidth    : 3,
						borderColor    : "#fff",
						hoverOffset    : 8
					}]
				},
				options: {
					responsive: true,
					cutout    : "62%",
					animation : { animateRotate: true, duration: 700 },
					plugins   : {
						legend: {
							position: "bottom",
							labels  : { font:{ size:11 }, padding:12, usePointStyle:true }
						},
						tooltip: {
							callbacks: {
								label: (ctx) => {
									const v   = ctx.parsed;
									const pct = counts.total > 0
										? " (" + Math.round((v / counts.total) * 100) + "%)"
										: "";
									return ` ${ctx.label}: ${v}${pct}`;
								}
							}
						}
					}
				}
			});

			/* ── Top Competitors bar ─────────────────────── */
			const compColors = [
				"#3b82f6","#8b5cf6","#06b6d4","#f59e0b",
				"#ec4899","#10b981","#f97316","#14b8a6",
				"#a855f7","#6366f1"
			];
			const trim = (s) => s.length > 18 ? s.slice(0, 17) + "…" : s;

			new Chart(c2, {
				type : "bar",
				data : {
					labels  : topComps.map((e) => trim(e[0])),
					datasets: [
						{
							label          : "Total Bids",
							data           : topComps.map((e) => e[1].bids),
							backgroundColor: compColors,
							borderRadius   : 6,
							borderSkipped  : false
						},
						{
							label          : "Wins",
							data           : topComps.map((e) => e[1].wins),
							backgroundColor: "#22c55e",
							borderRadius   : 6,
							borderSkipped  : false
						}
					]
				},
				options: {
					responsive  : true,
					animation   : { duration: 700 },
					plugins     : {
						legend : {
							position: "top",
							labels  : { font:{ size:11 }, usePointStyle:true }
						},
						tooltip: {
							callbacks: {
								label: (ctx) => ` ${ctx.dataset.label}: ${ctx.parsed.y}`
							}
						}
					},
					scales: {
						y: {
							beginAtZero: true,
							ticks: { stepSize:1, font:{ size:11 } },
							grid : { color:"rgba(0,0,0,0.05)" }
						},
						x: {
							grid : { display:false },
							ticks: { font:{ size:10 }, maxRotation:35 }
						}
					}
				}
			});

		}, 380);
	});
}


/* ─────────────────────────────────────────────────────────────
   STYLE INJECTION  (called once on onload)
───────────────────────────────────────────────────────────── */
function _bcInjectStyles() {
	if (document.getElementById("bc-bid-cmp-styles")) return;

	const style = document.createElement("style");
	style.id    = "bc-bid-cmp-styles";

	style.textContent = `

		/* ── DataTable row hover ─────────────────────────── */
		.dt-cell__content {
			transition: background .15s ease !important;
		}
		.dt-row:hover .dt-cell__content {
			background: rgba(30,77,183,.055) !important;
		}

		/* ── Summary wrap ───────────────────────────────── */
		#bc-summary-wrap {
			margin: 16px 0 20px 0;
		}

		/* ── 4-column card grid ─────────────────────────── */
		.bc-summary-grid {
			display: grid;
			grid-template-columns: repeat(4, minmax(0, 1fr));
			gap: 12px;
			width: 100%;
		}
		@media (max-width: 960px) {
			.bc-summary-grid {
				grid-template-columns: repeat(2, minmax(0, 1fr));
			}
		}
		@media (max-width: 560px) {
			.bc-summary-grid {
				grid-template-columns: 1fr;
			}
		}

		/* ── Card base ──────────────────────────────────── */
		.bc-summary-card {
			background    : #ffffff;
			border        : 1px solid #d1d8dd;
			border-radius : 12px;
			padding       : 16px 12px 14px 12px;
			text-align    : center;
			cursor        : pointer;
			position      : relative;
			overflow      : hidden;
			transition    :
				transform   .2s cubic-bezier(.34,1.56,.64,1),
				box-shadow  .2s ease,
				border-color .2s ease;
			box-shadow: 0 1px 4px rgba(0,0,0,0.06);
		}

		/* Coloured accent bar at top */
		.bc-summary-card::before {
			content      : "";
			display      : block;
			position     : absolute;
			top:0; left:0; right:0;
			height       : 4px;
			background   : var(--bc-accent, #1e4db7);
			border-radius: 12px 12px 0 0;
		}

		.bc-summary-card:hover {
			transform  : translateY(-4px) scale(1.02);
			box-shadow : 0 10px 28px rgba(30,77,183,.15);
			border-color: #b0bec5;
		}

		/* Active/selected card ring */
		.bc-summary-card.bc-card-active {
			box-shadow   : 0 0 0 3px rgba(30,77,183,.38);
			border-color : #1e4db7;
			transform    : translateY(-4px) scale(1.02);
		}

		/* ── Label ──────────────────────────────────────── */
		.bc-card-label {
			font-size     : 11px;
			font-weight   : 700;
			color         : #6c757d;
			margin-bottom : 8px;
			white-space   : nowrap;
			overflow      : hidden;
			text-overflow : ellipsis;
			text-transform: uppercase;
			letter-spacing: 0.5px;
		}

		/* ── Big number ─────────────────────────────────── */
		.bc-card-value {
			font-size  : 34px;
			font-weight: 800;
			line-height: 1.1;
		}

		/* Per-card colour classes */
		.bc-val-blue   { color: #1e4db7; }
		.bc-val-navy   { color: #1e40af; }
		.bc-val-green  { color: #15803d; }
		.bc-val-amber  { color: #92400e; }
		.bc-val-red    { color: #b91c1c; }
		.bc-val-slate  { color: #475569; }
		.bc-val-purple { color: #6d28d9; }
		.bc-val-teal   { color: #0f766e; }

		/* Hide Frappe's built-in summary (cards replace it) */
		.query-report .report-summary {
			display: none !important;
		}

		/* ── Row entrance animation ─────────────────────── */
		@keyframes _bcRowSlideIn {
			from { opacity:0; transform: translateX(-10px); }
			to   { opacity:1; transform: none; }
		}
		.dt-body .dt-row {
			animation: _bcRowSlideIn .28s ease both;
		}

		/* ── Monospace numeric columns ──────────────────── */
		[data-fieldtype="Currency"] .dt-cell__content,
		[data-fieldtype="Percent"]  .dt-cell__content,
		[data-fieldtype="Float"]    .dt-cell__content,
		[data-fieldtype="Int"]      .dt-cell__content {
			font-family: "JetBrains Mono","Fira Code",monospace !important;
			font-size  : 12px;
		}
	`;

	document.head.appendChild(style);
}