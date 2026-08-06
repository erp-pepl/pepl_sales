import frappe


PERMISSIONS = [
    {
        "role": "System Manager",
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "report": 1,
        "export": 1,
        "print": 1,
        "email": 1,
        "share": 1,
        "submit": 1,
        "cancel": 1,
    },
    {
        "role": "PEPL Tender Manager",
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "report": 1,
        "export": 1,
        "import": 1,
        "share": 1,
        "print": 1,
        "email": 1,
    },
    {
        "role": "PEPL Tender Executive",
        "read": 1,
        "write": 1,
        "create": 1,
        "report": 1,
        "share": 1,
        "print": 1,
        "email": 1,
    },
    {
        "role": "PEPL Tender Viewer",
        "read": 1,
        "report": 1,
        "print": 1,
    },
]


def execute():
    if not frappe.db.exists(
        "DocType",
        "PEPL Tender",
    ):
        return

    tender_doctype = frappe.get_doc(
        "DocType",
        "PEPL Tender",
    )

    tender_doctype.set(
        "permissions",
        [],
    )

    for permission in PERMISSIONS:
        tender_doctype.append(
            "permissions",
            permission,
        )

    tender_doctype.save(
        ignore_permissions=True
    )

    frappe.clear_cache(
        doctype="PEPL Tender"
    )
