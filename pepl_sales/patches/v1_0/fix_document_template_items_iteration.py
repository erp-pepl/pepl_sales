import frappe


# Jinja resolves ``obj.items`` against the Python attribute before
# falling back to the mapping key. The generation context passes
# ERPNext documents through ``as_dict()``, which returns a dict
# subclass, so ``sales_order.items`` returned the built-in
# ``dict.items`` method instead of the child table. The method is
# truthy, so it survived the ``or []`` guard and then failed with
# "'builtin_function_or_method' object is not iterable".
#
# Subscript access forces __getitem__ and returns the child table.

REPLACEMENTS = [
    [
        "{% for item in sales_order.items or [] %}",
        "{% for item in sales_order['items'] or [] %}",
    ],
    [
        "{% for item in sales_invoice.items or [] %}",
        "{% for item in sales_invoice['items'] or [] %}",
    ],
]


CORRECTED_VERSION = "1.1"


def execute():
    if not frappe.db.exists(
        "DocType",
        "PEPL Standard Document Template",
    ):
        return

    corrected = []

    for name in frappe.get_all(
        "PEPL Standard Document Template",
        pluck="name",
    ):
        html = frappe.db.get_value(
            "PEPL Standard Document Template",
            name,
            "html_template",
        )

        if not html:
            continue

        updated = html

        for pair in REPLACEMENTS:
            updated = updated.replace(
                pair[0],
                pair[1],
            )

        if updated == html:
            continue

        frappe.db.set_value(
            "PEPL Standard Document Template",
            name,
            "html_template",
            updated,
            update_modified=False,
        )

        frappe.db.set_value(
            "PEPL Standard Document Template",
            name,
            "template_version",
            CORRECTED_VERSION,
            update_modified=False,
        )

        corrected.append(name)

    frappe.clear_cache(
        doctype="PEPL Standard Document Template"
    )

    print(
        "Corrected item iteration in "
        + str(len(corrected))
        + " template(s)."
    )
