import frappe
from frappe.permissions import reset_perms


TENDER_DOCTYPE = "PEPL Tender"
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

    for user, configuration in PROFILE_ASSIGNMENTS.items():
        _create_and_assign_profile(
            user=user,
            source_profile=configuration["source_profile"],
            target_profile=configuration["target_profile"],
        )


def _reset_tender_permissions():
    if not frappe.db.exists(
        "DocType",
        TENDER_DOCTYPE,
    ):
        return

    reset_perms(TENDER_DOCTYPE)

    frappe.clear_cache(
        doctype=TENDER_DOCTYPE,
    )


def _create_and_assign_profile(
    user,
    source_profile,
    target_profile,
):
    if not frappe.db.exists("User", user):
        frappe.throw(
            "Required User does not exist: "
            + user
        )

    if not frappe.db.exists(
        "Role Profile",
        source_profile,
    ):
        frappe.throw(
            "Source Role Profile does not exist: "
            + source_profile
        )

    source_doc = frappe.get_doc(
        "Role Profile",
        source_profile,
    )

    roles = []

    for row in source_doc.get("roles") or []:
        if row.role and row.role not in roles:
            roles.append(row.role)

    if TENDER_EXECUTIVE_ROLE not in roles:
        roles.append(TENDER_EXECUTIVE_ROLE)

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

    for role in roles:
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
        user_doc.role_profile_name
        != target_profile
    ):
        frappe.throw(
            "Role Profile assignment did not persist "
            "for User: "
            + user
        )

    if (
        TENDER_EXECUTIVE_ROLE
        not in persisted_roles
    ):
        frappe.throw(
            "Tender Executive role did not persist "
            "for User: "
            + user
        )
