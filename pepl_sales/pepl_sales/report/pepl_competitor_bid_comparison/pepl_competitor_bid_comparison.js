/**
 * PEPL Competitor Bid Comparison — Enhanced Report JS
 * ─────────────────────────────────────────────────────
 * Frappe Script Report · PEPL Sales Module
 *
 * Enhancements over baseline:
 *   ① Smart date presets  (This Month / Quarter / FY)
 *   ② Column formatters   (colored badges, icons, mono numbers)
 *   ③ Embedded bar chart  (top-8 competitors: bids vs wins)
 *   ④ Row stagger animation on every render
 *   ⑤ Summary-card hover-lift effect
 *   ⑥ Monospace font for all currency / numeric columns
 */

frappe.query_reports["PEPL Competitor Bid Comparison"] = {

	/* ═══════════════════════════════════════════════════════════
	   1 ▸ FILTERS  (unchanged names + sensible defaults)
	═══════════════════════════════════════════════════════════ */
	filters: [
		{
			fieldname    : "from_date",
			label        : __("Outcome From Date"),
			fieldtype    : "Date",
			default      : frappe.datetime.add_months(frappe.datetime.get_today(), -3)
		},
		{
			fieldname    : "to_date",
			label        : __("Outcome To Date"),
			fieldtype    : "Date",
			default      : frappe.datetime.get_today()
		},
		{
			fieldname    : "tender",
			label        : __("Tender"),
			fieldtype    : "Link",
			options      : "PEPL Tender"
		},
		{
			fieldname    : "customer",
			label        : __("Customer"),
			fieldtype    : "Link",
			options      : "Customer"
		},
		{
			fieldname    : "sector",
			label        : __("Sector"),
			fieldtype    : "Select",
			options      : "\nRailways\nDefence\nPrivate\nOthers"
		},
		{
			fieldname    : "item",
			label        : __("Item"),
			fieldtype    : "Link",
			options      : "Item"
		},
		{
			fieldname    : "item_outcome",
			label        : __("Item Outcome"),
			fieldtype    : "Select",
			options      : "\nPending\nWon\nPartially Won\nLost\nCancelled"
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
			description  : __("1 = PEPL only · 0 = competitors only")
		},
		{
			fieldname    : "rank",
			label        : __("Rank"),
			fieldtype    : "Data",
			description  : __("Examples: L1, L2, L10")
		},
		{
			fieldname    : "winner_only",
			label        : __("Winner Only"),
			fieldtype    : "Check"
		}
	],

	/* ═══════════════════════════════════════════════════════════
	   2 ▸ CHART  — Top-8 competitors: total bids vs wins
	═══════════════════════════════════════════════════════════ */
	get_chart_data(columns, result) {
		if (!result || !result.length) return null;

		/* Aggregate per competitor (exclude PEPL rows) */
		var stats = {};
		result.forEach(function (row) {
			if (!row.competitor_name || row.is_pepl) return;
			if (!stats[row.competitor_name])
				stats[row.competitor_name] = { bids: 0, wins: 0 };
			stats[row.competitor_name].bids++;
			if (row.is_winner || row.buyer_selected)
				stats[row.competitor_name].wins++;
		});

		var top = Object.entries(stats)
			.sort(function (a, b) { return b[1].bids - a[1].bids; })
			.slice(0, 8);

		if (!top.length) return null;

		var trunc = function (s) { return s.length > 20 ? s.slice(0, 19) + "…" : s; };

		return {
			data: {
				labels  : top.map(function (x) { return trunc(x[0]); }),
				datasets: [
					{ name: __("Total Bids"), values: top.map(function (x) { return x[1].bids; }), chartType: "bar" },
					{ name: __("Wins"),       values: top.map(function (x) { return x[1].wins; }), chartType: "bar" }
				]
			},
			type       : "bar",
			colors     : ["#3b82f6", "#22c55e"],
			height     : 230,
			axisOptions: { xIsSeries: true },
			barOptions : { spaceRatio: 0.35 },
			tooltipOptions: {
				formatTooltipY: function (val) { return String(val); }
			}
		};
	},

	/* ═══════════════════════════════════════════════════════════
	   3 ▸ COLUMN FORMATTER
	═══════════════════════════════════════════════════════════ */
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		/* ── Item Outcome badge ───────────────────────── */
		if (column.fieldname === "item_outcome") {
			var MAP = {
				"Won"          : { bg:"#dcfce7", fg:"#15803d", bd:"#86efac", ic:"✓" },
				"Partially Won": { bg:"#fef3c7", fg:"#92400e", bd:"#fcd34d", ic:"◑" },
				"Lost"         : { bg:"#fee2e2", fg:"#b91c1c", bd:"#fca5a5", ic:"✗" },
				"Pending"      : { bg:"#f1f5f9", fg:"#475569", bd:"#cbd5e1", ic:"⏳" },
				"Cancelled"    : { bg:"#ede9fe", fg:"#6d28d9", bd:"#c4b5fd", ic:"⊘" }
			};
			var t = MAP[data.item_outcome] || MAP["Pending"];
			return (
				'<span style="display:inline-flex;align-items:center;gap:4px;' +
				'background:' + t.bg + ';color:' + t.fg + ';border:1px solid ' + t.bd + ';' +
				'padding:2px 10px;border-radius:20px;font-weight:700;font-size:11px;white-space:nowrap">' +
				t.ic + " " + (data.item_outcome || "—") + "</span>"
			);
		}

		/* ── Competitor name (PEPL badge) ─────────────── */
		if (column.fieldname === "competitor_name") {
			if (data.is_pepl) {
				return (
					'<span style="display:inline-flex;align-items:center;gap:5px;font-weight:700;color:#1e40af">' +
					'<span style="background:#1e4db7;color:#fff;padding:1px 7px;border-radius:4px;' +
					'font-size:10px;font-weight:800;letter-spacing:.6px;line-height:1.7">PEPL</span>' +
					(data.competitor_name || "") +
					"</span>"
				);
			}
			return '<span style="font-weight:500">' + (data.competitor_name || "—") + "</span>";
		}

		/* ── Rank badge ───────────────────────────────── */
		if (column.fieldname === "rank" && data.rank) {
			var RC = {
				"L1": ["#22c55e","#fff"],
				"L2": ["#f59e0b","#fff"],
				"L3": ["#fb923c","#fff"]
			};
			var rc = RC[data.rank] || ["#94a3b8","#fff"];
			return (
				'<span style="background:' + rc[0] + ';color:' + rc[1] + ';' +
				'padding:2px 10px;border-radius:20px;font-weight:800;font-size:11px;' +
				'box-shadow:0 1px 4px ' + rc[0] + '88">' + data.rank + "</span>"
			);
		}

		/* ── Sector badge ─────────────────────────────── */
		if (column.fieldname === "sector" && data.sector) {
			var SC = {
				"Railways": ["#eff6ff","#1d4ed8","#93c5fd"],
				"Defence" : ["#fff1f2","#be123c","#fca5a5"],
				"Private" : ["#f5f3ff","#6d28d9","#c4b5fd"],
				"Others"  : ["#f8fafc","#475569","#cbd5e1"]
			};
			var sc = SC[data.sector] || SC["Others"];
			return (
				'<span style="background:' + sc[0] + ';color:' + sc[1] + ';' +
				'border:1px solid ' + sc[2] + ';padding:2px 9px;border-radius:4px;' +
				'font-weight:600;font-size:11px">' + data.sector + "</span>"
			);
		}

		/* ── Δ from PEPL %  &  Δ from L1 % ──────────── */
		var PCT_FIELDS = ["difference_from_pepl_percent", "difference_from_l1_percent"];
		if (PCT_FIELDS.indexOf(column.fieldname) !== -1) {
			var v = parseFloat(data[column.fieldname]);
			if (isNaN(v) || v === 0) return '<span style="color:#94a3b8">—</span>';
			var pc = v < 0 ? "#15803d" : "#b91c1c";
			var pa = v < 0 ? "▼" : "▲";
			return (
				'<span style="color:' + pc + ';font-weight:700;' +
				'font-family:\'JetBrains Mono\',\'Fira Code\',monospace;font-size:12px">' +
				pa + " " + Math.abs(v).toFixed(2) + "%</span>"
			);
		}

		/* ── Boolean icon columns ─────────────────────── */
		if (column.fieldname === "is_winner")
			return data.is_winner
				? '<span style="font-size:14px" title="Winner">🏆</span>' : "";

		if (column.fieldname === "is_l1")
			return data.is_l1
				? '<span style="color:#15803d;font-size:15px;font-weight:900" title="L1 – Lowest Bidder">✓</span>' : "";

		if (column.fieldname === "buyer_selected")
			return data.buyer_selected
				? '<span style="color:#1d4ed8;font-size:14px" title="Buyer Selected">★</span>' : "";

		if (column.fieldname === "is_pepl")
			return data.is_pepl
				? '<span style="color:#1e4db7;font-size:14px">●</span>'
				: '<span style="color:#cbd5e1">○</span>';

		if (column.fieldname === "is_msme")
			return data.is_msme
				? '<span style="background:#fffbeb;color:#92400e;padding:1px 7px;border-radius:4px;' +
				  'font-size:10px;font-weight:700;border:1px solid #fcd34d">MSME</span>' : "";

		if (column.fieldname === "is_mii")
			return data.is_mii
				? '<span style="background:#eff6ff;color:#1e40af;padding:1px 7px;border-radius:4px;' +
				  'font-size:10px;font-weight:700;border:1px solid #93c5fd">MII</span>' : "";

		return value;
	},

	/* ═══════════════════════════════════════════════════════════
	   4 ▸ ON LOAD — inject CSS once, mount preset bar
	═══════════════════════════════════════════════════════════ */
	onload(report) {
		_peplInjectStyles();
		/* Wait for filter DOM to settle */
		setTimeout(function () { _peplMountPresets(report); }, 700);
	},

	/* ═══════════════════════════════════════════════════════════
	   5 ▸ AFTER RENDER — stagger row entrance animation
	═══════════════════════════════════════════════════════════ */
	after_render(_dt) {
		document.querySelectorAll(".dt-body .dt-row").forEach(function (row, i) {
			row.style.animationDelay = (i * 18) + "ms";
		});
	}
};


/* ═══════════════════════════════════════════════════════════════
   PRIVATE HELPERS
═══════════════════════════════════════════════════════════════ */

/** Inject stylesheet once per page lifetime */
function _peplInjectStyles() {
	if (document.getElementById("pepl-bid-cmp-styles")) return;

	var style = document.createElement("style");
	style.id = "pepl-bid-cmp-styles";
	style.textContent = [
		/* ── DataTable row hover ── */
		".dt-cell__content{transition:background .15s ease !important}",
		".dt-row:hover .dt-cell__content{background:rgba(30,77,183,.055) !important}",

		/* ── Summary card lift ── */
		".report-summary-wrapper .summary-card{",
		"  transition:transform .22s cubic-bezier(.34,1.56,.64,1),box-shadow .22s ease !important;",
		"  cursor:default",
		"}",
		".report-summary-wrapper .summary-card:hover{",
		"  transform:translateY(-4px) scale(1.025) !important;",
		"  box-shadow:0 14px 32px rgba(30,77,183,.16) !important",
		"}",

		/* ── Preset button bar ── */
		"#_pepl-presets{",
		"  display:flex;align-items:center;gap:6px;flex-wrap:wrap;",
		"  padding:8px 16px;margin:6px 0 12px;",
		"  background:linear-gradient(135deg,#f0f4ff,#e8f0fe);",
		"  border:1px solid #c7d7fb;border-radius:10px;",
		"}",
		"#_pepl-presets .pp-lbl{",
		"  font-size:11px;font-weight:700;color:#374151;",
		"  letter-spacing:.5px;text-transform:uppercase;margin-right:4px",
		"}",
		".pp-btn{",
		"  background:#fff;border:1.5px solid #c7d7fb;border-radius:20px;",
		"  padding:3px 14px;font-size:11px;font-weight:600;color:#1e4db7;",
		"  cursor:pointer;",
		"  transition:all .18s cubic-bezier(.34,1.56,.64,1);",
		"  outline:none",
		"}",
		".pp-btn:hover,.pp-btn.active{",
		"  background:#1e4db7;color:#fff;border-color:#1e4db7;",
		"  transform:translateY(-1px);box-shadow:0 4px 12px rgba(30,77,183,.28)",
		"}",
		".pp-btn-clear{background:#fee2e2 !important;border-color:#fca5a5 !important;color:#dc2626 !important}",
		".pp-btn-clear:hover{background:#dc2626 !important;color:#fff !important;border-color:#dc2626 !important}",

		/* ── Row stagger animation ── */
		"@keyframes _ppRowIn{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}",
		".dt-body .dt-row{animation:_ppRowIn .28s ease both}",

		/* ── Monospace for numeric columns ── */
		"[data-fieldtype='Currency'] .dt-cell__content,",
		"[data-fieldtype='Percent']  .dt-cell__content,",
		"[data-fieldtype='Float']    .dt-cell__content,",
		"[data-fieldtype='Int']      .dt-cell__content{",
		"  font-family:'JetBrains Mono','Fira Code',monospace !important;",
		"  font-size:12px",
		"}"
	].join("\n");

	document.head.appendChild(style);
}


/** Render the Quick-Filter preset bar above the filter form */
function _peplMountPresets(report) {
	if (document.getElementById("_pepl-presets")) return;

	var wrap =
		document.querySelector(".standard-filter-section") ||
		document.querySelector(".filter-section");
	if (!wrap) return;

	var PRESETS = [
		"This Month", "Last Month",
		"This Quarter", "Last Quarter",
		"This FY", "Last FY"
	];

	var btnHtml = PRESETS.map(function (label) {
		return '<button class="pp-btn" data-key="' + label + '">' + label + "</button>";
	}).join("");
	btnHtml += '<button class="pp-btn pp-btn-clear" data-key="Clear">✕ Clear</button>';

	var bar = document.createElement("div");
	bar.id = "_pepl-presets";
	bar.innerHTML = '<span class="pp-lbl">⚡ Quick:</span>' + btnHtml;
	wrap.insertAdjacentElement("afterbegin", bar);

	bar.querySelectorAll(".pp-btn").forEach(function (btn) {
		btn.addEventListener("click", function () {
			bar.querySelectorAll(".pp-btn").forEach(function (b) { b.classList.remove("active"); });
			btn.classList.add("active");
			_peplApplyPreset(btn.dataset.key, report);
		});
	});
}


/** Compute date range and refresh the report */
function _peplApplyPreset(key, report) {
	var today = frappe.datetime.get_today();
	var now   = new Date();
	var fyY   = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;

	/* Helper: JS Date → Frappe date string */
	var dStr  = function (dateObj) { return frappe.datetime.obj_to_str(dateObj); };

	/* Helper: safe month-start of a Frappe date string */
	var mStart = function (ds) {
		var d = frappe.datetime.str_to_obj(ds);
		d.setDate(1);
		return dStr(d);
	};
	/* Helper: safe month-end of a Frappe date string */
	var mEnd = function (ds) {
		var d = frappe.datetime.str_to_obj(ds);
		d.setMonth(d.getMonth() + 1);
		d.setDate(0);
		return dStr(d);
	};

	var from, to;

	switch (key) {

		case "This Month":
			from = mStart(today);
			to   = mEnd(today);
			break;

		case "Last Month": {
			var lm = frappe.datetime.add_months(today, -1);
			from   = mStart(lm);
			to     = mEnd(lm);
			break;
		}

		case "This Quarter": {
			var q  = Math.floor(now.getMonth() / 3);
			from   = dStr(new Date(now.getFullYear(), q * 3, 1));
			to     = dStr(new Date(now.getFullYear(), (q + 1) * 3, 0));
			break;
		}

		case "Last Quarter": {
			var lq  = Math.floor(now.getMonth() / 3) - 1;
			var lqY = lq < 0 ? now.getFullYear() - 1 : now.getFullYear();
			var lqa = lq < 0 ? 3 : lq;
			from    = dStr(new Date(lqY, lqa * 3, 1));
			to      = dStr(new Date(lqY, (lqa + 1) * 3, 0));
			break;
		}

		case "This FY":
			from = fyY + "-04-01";
			to   = (fyY + 1) + "-03-31";
			break;

		case "Last FY":
			from = (fyY - 1) + "-04-01";
			to   = fyY + "-03-31";
			break;

		case "Clear":
			report.set_filter_value("from_date", "");
			report.set_filter_value("to_date",   "");
			report.refresh();
			return;

		default:
			return;
	}

	report.set_filter_value("from_date", from);
	report.set_filter_value("to_date",   to);
	report.refresh();
}