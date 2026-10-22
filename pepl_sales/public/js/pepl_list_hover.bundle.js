// PEPL - List View hover preview ("Option B" card).
// Rest the mouse anywhere on a row of any List View: after half a second a card shows that record -
// a status-coloured strip, number + status, grey chips with the main fields, the amount in large type,
// the item table with a Total row and, on submitted documents, GL Entries / Stock Movement.
// Data: pepl_sales.list_preview.get_preview (permission-checked on the server).
// Built as a Frappe bundle, so every change gets a new file name and no browser keeps an old copy.
(() => {
	if (window.__pepl_list_preview_bound) return;
	window.__pepl_list_preview_bound = true;

	const METHOD = "pepl_sales.list_preview.get_preview";
	const ROW = ".frappe-list .list-row-container";
	const SHOW_DELAY = 500; // resting time before the card opens, so passing over the list opens nothing
	const SWITCH_DELAY = 150; // quicker when a card is already open and the cursor moves to another row
	const HIDE_DELAY = 300; // time to move the cursor from the row onto the card (to click its link)
	const MAX_WIDTH = 560;
	// Where the card opens. Across: always centred over the list area (never at the screen edge).
	// Up/down: "row" = just below the row (above it near the bottom of the screen), so it never covers the row
	// under the mouse; "center" = in the middle of the screen.
	const VERTICAL = "row";

	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	let cache = new Map(); // "doctype::name::modified" -> server reply
	let cache_owner = null; // the list data the cache belongs to; a list refresh starts a new cache
	let hover_row = null;
	let show_timer = null;
	let hide_timer = null;
	let active_key = null;
	let card = null;

	function enabled() {
		if (window.matchMedia && !window.matchMedia("(hover: hover)").matches) return false; // touch
		if (frappe.is_mobile && frappe.is_mobile()) return false;
		if (document.querySelector(".modal.show")) return false;
		const list = window.cur_list;
		return !!(list && list.doctype && list.view_name === "List");
	}

	// v16 keeps the plain name on the row checkbox (older releases URI-encoded it)
	function row_name(row) {
		const box = row.querySelector(".list-row-checkbox");
		const raw = (box && box.dataset.name) || row.querySelector("a[data-name]")?.dataset.name;
		if (!raw) return null;
		if ((window.cur_list?.data || []).some((d) => d.name === raw)) return raw;
		try {
			return decodeURIComponent(raw);
		} catch {
			return raw;
		}
	}

	function row_modified(name) {
		const doc = (window.cur_list?.data || []).find((d) => d.name === name);
		return doc ? doc.modified || "" : "";
	}

	// The status Frappe already drew in the row: its text and its exact colours (any theme, light or dark)
	function row_status(row) {
		const badge =
			row.querySelector('[data-fieldname="status_field"] .es-badge') ||
			row.querySelector(".es-badge[data-filter]") ||
			row.querySelector(".indicator-pill");
		if (!badge) return null;
		const label = (badge.querySelector(".es-badge__label") || badge).textContent.trim();
		if (!label) return null;
		const css = getComputedStyle(badge);
		const text = css.getPropertyValue("--c-fg").trim() || css.color;
		const strip = css.getPropertyValue("--c-solid-bg").trim() || text;
		return { label, text, strip };
	}

	function get_card() {
		if (!card) {
			card = document.createElement("div");
			// self-contained styling (pepl_list_hover.bundle.css); no dependency on Frappe popover styles
			card.className = "pepl-hp";
			card.hidden = true;
			card.addEventListener("mouseenter", () => {
				clearTimeout(hide_timer);
				clearTimeout(show_timer);
			});
			card.addEventListener("mouseleave", schedule_hide);
			card.addEventListener("click", (e) => {
				if (e.target.closest(".pepl-hp-close")) hide();
				else if (e.target.closest("a")) setTimeout(hide, 0);
			});
			document.body.appendChild(card);
		}
		return card;
	}

	function hide() {
		clearTimeout(show_timer);
		clearTimeout(hide_timer);
		active_key = null;
		if (card) {
			card.hidden = true;
			card.innerHTML = "";
		}
	}

	function schedule_hide() {
		clearTimeout(hide_timer);
		hide_timer = setTimeout(hide, HIDE_DELAY);
	}

	function place(row) {
		const c = get_card();
		const rect = row.getBoundingClientRect();
		const vw = window.innerWidth;
		const vh = window.innerHeight;
		const gap = 8;
		const margin = 12;
		const width = Math.min(MAX_WIDTH, vw - 2 * margin);

		c.style.width = width + "px";
		c.style.maxHeight = Math.round(vh * 0.8) + "px";
		const h = c.offsetHeight;

		// across: centred over the list (the page's main area), kept inside the window
		const area = (row.closest(".frappe-list") || document.body).getBoundingClientRect();
		let left = area.left + (area.width - width) / 2;
		left = Math.min(Math.max(margin, left), vw - width - margin);

		// up/down
		let top;
		if (VERTICAL === "center") {
			top = (vh - h) / 2;
		} else if (rect.bottom + gap + h <= vh - margin) {
			top = rect.bottom + gap; // below the row
		} else if (rect.top - gap - h >= margin) {
			top = rect.top - gap - h; // above the row
		} else {
			top = (vh - h) / 2; // no room either side: middle of the screen
		}
		top = Math.max(margin, top);

		c.style.top = Math.round(top) + "px";
		c.style.left = Math.round(left) + "px";
	}

	function table_html(t, with_title) {
		const num = (i) => !!(t.columns[i] && t.columns[i].numeric);
		const cell = (v, i, tag) => {
			const cls = num(i) ? "pepl-hp-num" : i === 0 ? "pepl-hp-first" : "";
			const tip = i === 0 && v ? ` title="${esc(v)}"` : "";
			return `<${tag}${cls ? ` class="${cls}"` : ""}${tip}>${esc(v)}</${tag}>`;
		};
		const head = t.columns.map((c, i) => cell(c.label, i, "th")).join("");
		const body = t.rows.map((r) => `<tr>${r.map((v, i) => cell(v, i, "td")).join("")}</tr>`).join("");
		const foot = t.totals
			? `<tfoot><tr>${t.totals.map((v, i) => cell(v, i, "td")).join("")}</tr></tfoot>`
			: "";
		const more = t.more ? `<div class="pepl-hp-more">${esc(__("+ {0} more rows", [t.more]))}</div>` : "";
		return `
			<div class="pepl-hp-section">
				${with_title ? `<div class="pepl-hp-section-title">${esc(t.label)}</div>` : ""}
				<div class="pepl-hp-tablewrap">
					<table class="pepl-hp-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody>${foot}</table>
				</div>
				${more}
			</div>`;
	}

	function render(data, doctype, name, status) {
		if (!data || data.hidden || data.missing || data.denied) return false;
		const c = get_card();

		// the status line already shows the status; leave out any chip that repeats it
		// the status line at the top already shows the status (as the list shows it, e.g. "Overdue"),
		// so no Status chip
		let fields = data.header || [];
		if (status) fields = fields.filter((f) => f.fieldname !== "status" && f.value !== status.label);

		const values = new Set(fields.map((f) => f.value));
		const subtitle =
			data.title && data.title !== name && !values.has(data.title)
				? `<div class="pepl-hp-sub" title="${esc(data.title)}">${esc(data.title)}</div>`
				: "";
		const chips = fields
			.map(
				(f) =>
					`<span class="pepl-hp-chip"><span class="pepl-hp-chip-label">${esc(
						f.label
					)}</span>${esc(f.value)}</span>`
			)
			.join("");
		const amount = data.highlight
			? `<div class="pepl-hp-amount"><span class="pepl-hp-amount-label">${esc(
					data.highlight.label
			  )}</span><span class="pepl-hp-amount-value">${esc(data.highlight.value)}</span></div>`
			: "";
		const sections = [...(data.tables || []), ...(data.ledgers || [])];

		c.style.setProperty("--pepl-hp-strip", status ? status.strip : "");
		c.style.setProperty("--pepl-hp-status", status ? status.text : "");
		c.classList.toggle("pepl-hp-has-status", !!status);
		c.innerHTML = `
			<button type="button" class="pepl-hp-close" aria-label="${esc(__("Close"))}">&times;</button>
			<div class="pepl-hp-head">
				<div class="pepl-hp-id">
					<a class="pepl-hp-name" href="${esc(frappe.utils.get_form_link(doctype, name))}">${esc(name)}</a>
					<div class="pepl-hp-type">${esc(__(doctype))}</div>
				</div>
				${
					status
						? `<div class="pepl-hp-status"><span class="pepl-hp-dot"></span>${esc(status.label)}</div>`
						: ""
				}
			</div>
			${subtitle}
			${chips ? `<div class="pepl-hp-chips">${chips}</div>` : ""}
			${amount}
			${sections.map((t) => table_html(t, sections.length > 1)).join("")}
		`;
		return true;
	}

	function show(row) {
		const c = get_card();
		c.hidden = false;
		place(row);
	}

	function open_for(row) {
		if (!enabled() || !row.isConnected) return;
		const list = window.cur_list;
		const doctype = list.doctype;
		const name = row_name(row);
		if (!name) return;

		if (cache_owner !== list.data) {
			cache = new Map();
			cache_owner = list.data;
		}

		const key = `${doctype}::${name}::${row_modified(name)}`;
		if (key === active_key && card && !card.hidden) return;
		active_key = key;
		const status = row_status(row);

		if (cache.has(key)) {
			if (render(cache.get(key), doctype, name, status)) show(row);
			else hide();
			return;
		}

		const c = get_card();
		c.style.setProperty("--pepl-hp-strip", status ? status.strip : "");
		c.classList.toggle("pepl-hp-has-status", !!status);
		c.innerHTML = `<div class="pepl-hp-loading">${esc(__("Loading..."))}</div>`;
		show(row);

		frappe.call({
			method: METHOD,
			type: "GET",
			args: { doctype, name },
			freeze: false,
			callback(r) {
				cache.set(key, r.message);
				if (active_key !== key) return; // the cursor has already moved on
				if (render(r.message, doctype, name, status) && row.isConnected) place(row);
				else hide();
			},
			error() {
				if (active_key === key) hide();
			},
		});
	}

	// ---- events (capture phase, so this runs before Frappe's own hover handlers)

	document.addEventListener(
		"mouseover",
		(e) => {
			const row = e.target instanceof Element ? e.target.closest(ROW) : null;
			if (!row || !enabled()) return;
			// One card only: Frappe's own link preview (DocTypes with "Show Preview Popup") stays out of list rows
			if (e.target.closest("a[data-doctype]")) e.stopPropagation();
			if (row === hover_row) return;
			hover_row = row;
			clearTimeout(hide_timer);
			clearTimeout(show_timer);
			show_timer = setTimeout(() => open_for(row), active_key ? SWITCH_DELAY : SHOW_DELAY);
		},
		true
	);

	document.addEventListener(
		"mouseout",
		(e) => {
			const row = e.target instanceof Element ? e.target.closest(ROW) : null;
			if (!row || (e.relatedTarget instanceof Node && row.contains(e.relatedTarget))) return;
			if (hover_row === row) hover_row = null;
			clearTimeout(show_timer);
			if (active_key) schedule_hide();
		},
		true
	);

	// clicking a row (to open it or tick it) closes the card
	document.addEventListener(
		"mousedown",
		(e) => {
			if (e.target instanceof Element && e.target.closest(ROW)) hide();
		},
		true
	);

	document.addEventListener("keydown", (e) => {
		if (e.key === "Escape") hide();
	});

	// scrolling the list moves the row away from the card; scrolling inside the card is fine
	document.addEventListener(
		"scroll",
		(e) => {
			if (!active_key) return;
			if (card && e.target instanceof Node && card.contains(e.target)) return;
			hide();
		},
		{ capture: true, passive: true }
	);

	window.addEventListener("resize", hide);
	$(document).on("page-change", hide);
	if (frappe.router && typeof frappe.router.on === "function") frappe.router.on("change", hide);
})();
