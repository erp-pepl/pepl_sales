import frappe

MAX_LEN = 140


def build_item_summary(doc):
    names = []
    for row in doc.get("items") or []:
        name = (row.item_name or row.item_code or "").strip()
        if name and name not in names:
            names.append(name)

    summary = ", ".join(names)
    if len(summary) > MAX_LEN:
        summary = summary[: MAX_LEN - 1].rstrip(", ") + "…"
    return summary


def set_item_summary(doc, method=None):
    """Draft orders: runs on every save."""
    doc.custom_item_summary = build_item_summary(doc)


def sync_item_summary(doc, method=None):
    """Submitted orders: runs after 'Update Items' changes rows."""
    summary = build_item_summary(doc)
    if doc.custom_item_summary != summary:
        doc.db_set("custom_item_summary", summary, update_modified=False)