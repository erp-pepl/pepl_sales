import frappe


LETTERHEAD_VERSION = "PEPL-LH-2026-01"


def execute():
    if not frappe.db.exists(
        "DocType",
        "PEPL Standard Document Template",
    ):
        return

    templates = frappe.get_all(
        "PEPL Standard Document Template",
        fields=["name", "letterhead_version"],
        limit_page_length=0,
    )

    for template in templates:
        if (
            template.letterhead_version
            != LETTERHEAD_VERSION
        ):
            frappe.db.set_value(
                "PEPL Standard Document Template",
                template.name,
                "letterhead_version",
                LETTERHEAD_VERSION,
                update_modified=False,
            )

    frappe.clear_cache(
        doctype=(
            "PEPL Standard Document Template"
        )
    )
