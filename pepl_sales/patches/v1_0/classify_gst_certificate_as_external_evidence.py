import frappe


REQUIREMENT_NAME = "GST_CERTIFICATE"
TEMPLATE_NAME = "TPL_GST_CERTIFICATE"


def execute():
    _configure_requirement()
    _configure_template()


def _configure_requirement():
    if not frappe.db.exists(
        "PEPL Document Requirement",
        REQUIREMENT_NAME,
    ):
        return

    frappe.db.set_value(
        "PEPL Document Requirement",
        REQUIREMENT_NAME,
        {
            "evidence_required": 1,
            "mandatory": 0,
            "blocking_event": "None",
            "active": 1,
        },
        update_modified=False,
    )


def _configure_template():
    if not frappe.db.exists(
        "PEPL Standard Document Template",
        TEMPLATE_NAME,
    ):
        return

    frappe.db.set_value(
        "PEPL Standard Document Template",
        TEMPLATE_NAME,
        {
            "active": 0,
            "status": "Draft",
        },
        update_modified=False,
    )
