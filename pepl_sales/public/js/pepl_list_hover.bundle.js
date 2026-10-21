// PEPL: hover anywhere on a list row to see a preview card of that record.
// One white card (Frappe preview styling), works on every DocType's list view.
(() => {
	if (window.__pepl_row_preview_bound) return;
	window.__pepl_row_preview_bound = true;

	const SHOW_DELAY_MS = 150;
	const MAX_FIELDS = 8;
	const MAX_VALUE_LEN = 120;
	const ROW_SELECTOR = ".list-row-container, .list-row";
	const SKIP_TYPES = [
		"Section Break", "Column Break", "Tab Break", "Fold", "Heading",
		"HTML", "Button", "Table", "Table MultiSelect", "Image", "Attach Image",
		"Signature", "Text Editor", "HTML Editor", "Markdown Editor", "Code",
		"Geolocation", "JSON", "Password",
	];

	let $card = null;
	let current_row = null;
	let show_timer = null;

	const esc = (v) => frappe.utils.escape_html(String(v ?? ""));
	const slug = (doctype) =>
		frappe.router && frappe.router.slug
			? frappe.router.slug(doctype)
			: doctype.toLowerCase().replace(/ /g, "-");

	function active_list() {
		const list = window.cur_list;
		const route = frappe.get_route ? frappe.get_route() : [];
		if (!list || !list.doctype || !Array.isArray(list.data)) return null;
		return route[0] === "List" ? list : null;
	}

	function get_row_name(row_el, list) {
		const cb = row_el.querySelector(".list-row-checkbox[data-name]");
		if (cb && cb.getAttribute("data-name")) return cb.getAttribute("data-name");

		const marker = `/${slug(list.doctype)}/`;
		for (const a of row_el.querySelectorAll("a[href]")) {
			const href = a.getAttribute("href") || "";
			const pos = href.indexOf(marker);
			if (pos === -1) continue;
			const name = decodeURIComponent(href.slice(pos + marker.length).split(/[?#]/)[0]);
			if (name) return name;
		}
		return null;
	}

	// Stop the browser's black tooltip and Frappe's own link card on this row.
	function silence_native(row_el) {
		row_el.querySelectorAll("a[data-doctype]").forEach((el) => {
			el.setAttribute("data-pepl-doctype", el.getAttribute("data-doctype"));
			el.removeAttribute("data-doctype");
		});
		row_el.querySelectorAll("a[title]").forEach((el) => {
			el.setAttribute("data-pepl-title", el.getAttribute("title"));
			el.removeAttribute("title");
		});
	}

	function to_text(value, df, row) {
		if (df.fieldtype === "Check") return cint(value) ? __("Yes") : __("No");
		let html;
		try {
			html = frappe.format(value, df, { inline: true }, row);
		} catch (e) {
			html = value;
		}
		return $("<div>").html(String(html ?? "")).text().trim();
	}

	function build_card_html(list, row) {
		const meta = frappe.get_meta(list.doctype);
		const fields = [];
		const shown = new Set();

		let title = row.name;
		if (meta && meta.title_field && row[meta.title_field]) {
			const tdf = meta.fields.find((f) => f.fieldname === meta.title_field);
			title = tdf ? to_text(row[meta.title_field], tdf, row) || row.name : String(row[meta.title_field]);
			shown.add(meta.title_field);
		}

		(meta ? meta.fields : []).forEach((df) => {
			if (fields.length >= MAX_FIELDS || shown.has(df.fieldname)) return;
			if (!(df.in_list_view || df.in_preview)) return;
			if (df.hidden || SKIP_TYPES.includes(df.fieldtype)) return;
			const value = row[df.fieldname];
			if (value === undefined || value === null || value === "") return;
			const text = to_text(value, df, row);
			if (!text) return;
			fields.push({ label: df.label || df.fieldname, text });
			shown.add(df.fieldname);
		});

		if (!shown.has("status") && row.status && fields.length < MAX_FIELDS) {
			fields.push({ label: "Status", text: String(row.status) });
		}

		const fields_html = fields
			.map(
				(f) => `
				<div class="preview-field">
					<div class="preview-label text-muted">${esc(__(f.label))}</div>
					<div class="preview-value">${esc(frappe.ellipsis(f.text, MAX_VALUE_LEN))}</div>
				</div>`
			)
			.join("");

		return `
			<div class="preview-popover-header">
				<div class="preview-header">
					<div class="preview-image">${frappe.get_avatar("avatar-medium", title)}</div>
					<div class="preview-name"><a>${esc(title)}</a></div>
					${title !== row.name ? `<div class="text-muted preview-title">${esc(row.name)}</div>` : ""}
				</div>
			</div>
			${fields_html ? `<hr><div class="popover-body"><div class="preview-table">${fields_html}</div></div>` : ""}
		`;
	}

	function ensure_card() {
		if ($card) return $card;
		$card = $(`
			<div class="link-preview-popover popover pepl-row-preview" role="tooltip">
				<div class="popover-body popover-content"></div>
			</div>
		`)
			.css({
				position: "absolute",
				display: "none",
				"pointer-events": "none",
				"min-width": "280px",
				"max-width": "420px",
				"z-index": 1070,
			})
			.appendTo(document.body);
		return $card;
	}

	function place(row_el) {
		const r = row_el.getBoundingClientRect();
		const h = $card.outerHeight();
		const w = $card.outerWidth();

		let top = r.bottom + 6;
		if (top + h > window.innerHeight - 8) top = Math.max(8, r.top - h - 6);

		let left = Math.min(r.left + 24, window.innerWidth - w - 8);
		left = Math.max(8, left);

		$card.css({ top: top + window.scrollY, left: left + window.scrollX });
	}

	function hide() {
		clearTimeout(show_timer);
		current_row = null;
		if ($card) $card.hide();
	}

	// Capture phase: runs before Frappe's own hover handlers.
	document.addEventListener(
		"mouseover",
		(e) => {
			const list = active_list();
			if (!list) return hide();

			const row_el = e.target && e.target.closest ? e.target.closest(ROW_SELECTOR) : null;
			if (!row_el) return hide();

			silence_native(row_el);
			if (row_el === current_row) return;

			const name = get_row_name(row_el, list);
			const row = name ? list.data.find((d) => d.name === name) : null;
			if (!row) return hide();

			current_row = row_el;
			clearTimeout(show_timer);
			if ($card) $card.hide();

			show_timer = setTimeout(() => {
				if (current_row !== row_el) return;
				const $c = ensure_card();
				$c.find(".popover-content").html(build_card_html(list, row));
				$c.css({ display: "block", visibility: "hidden" });
				place(row_el);
				$c.css("visibility", "visible");
			}, SHOW_DELAY_MS);
		},
		true
	);

	document.addEventListener("mouseout", (e) => {
		if (!e.relatedTarget) hide();
	});
	document.addEventListener("mousedown", hide, true);
	window.addEventListener("scroll", hide, true);
	if (frappe.router && frappe.router.on) frappe.router.on("change", hide);
})();