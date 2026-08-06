import frappe
from frappe.permissions import reset_perms


DOCTYPE_NAME = "PEPL Tender"
TENDER_EXECUTIVE_ROLE = "PEPL Tender Executive"

PROFILE_ASSIGNMENTS = {
    "dixitanshiv@gmail.com": {
        "source_profile": "Sales HOD",
        "target_profile":
            "Sales HOD - PEPL Tender Executive",
    },
    "dixitanshiv123@gmail.com": {
        "source_profile": "Sales",
        "target_profile":
            "Sales - PEPL Tender Executive",
    },
}


def execute():
    _reset_tender_permissions()
    _configure_tender_role_profiles()


def _reset_tender_permissions():
    if not frappe.db.exists(
        "DocType",
        DOCTYPE_NAME,
    ):
        return

    reset_perms(DOCTYPE_NAME)

    frappe.clear_cache(
        doctype=DOCTYPE_NAME,
    )


def _configure_tender_role_profiles():
    if not frappe.db.exists(
        "Role",
        TENDER_EXECUTIVE_ROLE,
    ):
        frappe.throw(
            "Required role is missing: "
            + TENDER_EXECUTIVE_ROLE
        )

    for user, config in PROFILE_ASSIGNMENTS.items():
        _configure_user_profile(
            user=user,
            source_profile=config["source_profile"],
            target_profile=config["target_profile"],
        )


def _configure_user_profile(
    user,
    source_profile,
    target_profile,
):
    if not frappe.db.exists("User", user):
        frappe.throw(
            "Required User is missing: " + user
        )

    if not frappe.db.exists(
        "Role Profile",
        source_profile,
    ):
        frappe.throw(
            "Source Role Profile is missing: "
            + source_profile
        )

    source_doc = frappe.get_doc(
        "Role Profile",
        source_profile,
    )

    source_roles = [
        row.role
        for row in source_doc.get("roles") or []
        if row.role
    ]

    final_roles = []

    for role in (
        source_roles
        + [TENDER_EXECUTIVE_ROLE]
    ):
        if role not in final_roles:
            final_roles.append(role)

    if frappe.db.exists(
        "Role Profile",
        target_profile,
    ):
        target_doc = frappe.get_doc(
            "Role Profile",
            target_profile,
        )
    else:
        target_doc = frappe.new_doc(
            "Role Profile"
        )
        target_doc.role_profile = target_profile

    target_doc.set("roles", [])

    for role in final_roles:
        target_doc.append(
            "roles",
            {
                "role": role,
            },
        )

    if target_doc.is_new():
        target_doc.insert(
            ignore_permissions=True,
        )
    else:
        target_doc.save(
            ignore_permissions=True,
        )

    user_doc = frappe.get_doc(
        "User",
        user,
    )

    user_doc.role_profile_name = target_profile
    user_doc.save(
        ignore_permissions=True,
    )

    user_doc.reload()

    persisted_roles = {
        row.role
        for row in user_doc.get("roles") or []
    }

    if (
        TENDER_EXECUTIVE_ROLE
        not in persisted_roles
    ):
        frappe.throw(
            "Tender Executive role did not persist "
            "for User: "
            + user
        )
