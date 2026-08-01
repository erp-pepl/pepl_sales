from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate, today

from pepl_sales.pepl_sales.doctype.pepl_system_parameters.pepl_system_parameters import (
    get_param,
)


RULE_TENDER_DEADLINE = "TENDER-DEADLINE"
RULE_DOCUMENT_PENDING = "DOCUMENT-PENDING"
RULE_PAYMENT_AGEING = "PAYMENT-AGEING"
RULE_VENDOR_APPROVAL = "VENDOR-APPROVAL"
RULE_PSD_EXPIRY = "PSD-EXPIRY"
RULE_PSD_REFUND = "PSD-REFUND"

TERMINAL_TENDER_STATUSES = {
    "Submitted",
    "Won",
    "Partially Won",
    "Order Received",
    "Lost",
    "No Bid",
    "Cancelled",
    "Re-tendered",
}

CLOSED_PAYMENT_STATUSES = {
    "Reconciled",
    "Closed",
}

CLOSED_PSD_STATUSES = {
    "PSD Refunded",
    "Closed",
    "PSD Not Required",
}


def _empty_result():
    return {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "closed": 0,
    }


def _record_action(result, action):
    if action in result:
        result[action] += 1


def _rule_marker(rule_code):
    return "PEPL-OPS::{0}".format(rule_code)


def _valid_system_user(user):
    if not user:
        return False

    user_data = frappe.db.get_value(
        "User",
        user,
        [
            "enabled",
            "user_type",
        ],
        as_dict=True,
    )

    return bool(
        user_data
        and user_data.enabled
        and user_data.user_type == "System User"
    )


def get_notification_owner(functional_field):
    """Return the functional owner, falling back to the configured owner."""
    owner = get_param(functional_field)

    if _valid_system_user(owner):
        return owner

    fallback = get_param("notification_fallback_owner")

    if _valid_system_user(fallback):
        return fallback

    frappe.throw(
        _(
            "No valid notification owner is configured for {0}, "
            "and Notification Fallback Owner is unavailable."
        ).format(functional_field)
    )


def _assigned_by_user():
    session_user = getattr(frappe.session, "user", None)

    if _valid_system_user(session_user):
        return session_user

    fallback = get_param("notification_fallback_owner")

    if _valid_system_user(fallback):
        return fallback

    return "Administrator"


def upsert_operational_todo(
    *,
    rule_code,
    reference_type,
    reference_name,
    allocated_to,
    description,
    priority="Medium",
    due_date=None,
):
    """Create or update one open ToDo for one rule and source document."""
    marker = _rule_marker(rule_code)

    if marker not in description:
        description = marker + "\n\n" + description

    existing_rows = frappe.get_all(
        "ToDo",
        filters={
            "status": "Open",
            "reference_type": reference_type,
            "reference_name": reference_name,
            "description": [
                "like",
                "%" + marker + "%",
            ],
        },
        fields=["name"],
        order_by="creation asc",
        limit_page_length=0,
    )

    # Defensive cleanup if historical duplicates exist.
    if len(existing_rows) > 1:
        for duplicate in existing_rows[1:]:
            frappe.db.set_value(
                "ToDo",
                duplicate.name,
                "status",
                "Closed",
                update_modified=True,
            )

    if existing_rows:
        todo = frappe.get_doc(
            "ToDo",
            existing_rows[0].name,
        )

        changed = False

        existing_values = {
            "allocated_to": todo.allocated_to or "",
            "description": todo.description or "",
            "priority": todo.priority or "",
            "date": (
                getdate(todo.date)
                if todo.date
                else None
            ),
            "reference_type": todo.reference_type or "",
            "reference_name": todo.reference_name or "",
        }

        expected_values = {
            "allocated_to": allocated_to or "",
            "description": description or "",
            "priority": priority or "",
            "date": (
                getdate(due_date)
                if due_date
                else getdate(today())
            ),
            "reference_type": reference_type or "",
            "reference_name": reference_name or "",
        }

        for fieldname, expected_value in expected_values.items():
            if existing_values[fieldname] == expected_value:
                continue

            value_to_set = expected_value

            if (
                fieldname != "date"
                and value_to_set == ""
            ):
                value_to_set = None

            todo.set(
                fieldname,
                value_to_set,
            )
            changed = True

        if changed:
            todo.save(ignore_permissions=True)

            return {
                "action": "updated",
                "name": todo.name,
            }

        return {
            "action": "unchanged",
            "name": todo.name,
        }

    todo = frappe.new_doc("ToDo")
    todo.status = "Open"
    todo.priority = priority
    todo.date = due_date or today()
    todo.allocated_to = allocated_to
    todo.assigned_by = _assigned_by_user()
    todo.reference_type = reference_type
    todo.reference_name = reference_name
    todo.description = description

    todo.insert(ignore_permissions=True)

    return {
        "action": "created",
        "name": todo.name,
    }


def close_resolved_rule_todos(
    *,
    rule_code,
    reference_type,
    active_reference_names,
):
    """Close open rule ToDos whose source is no longer an exception."""
    marker = _rule_marker(rule_code)
    active_names = set(active_reference_names or [])

    todo_rows = frappe.get_all(
        "ToDo",
        filters={
            "status": "Open",
            "reference_type": reference_type,
            "description": [
                "like",
                "%" + marker + "%",
            ],
        },
        fields=[
            "name",
            "reference_name",
        ],
        limit_page_length=0,
    )

    closed = 0

    for row in todo_rows:
        if row.reference_name in active_names:
            continue

        frappe.db.set_value(
            "ToDo",
            row.name,
            "status",
            "Closed",
            update_modified=True,
        )
        closed += 1

    return closed


def process_tender_deadline_exceptions():
    result = _empty_result()

    alert_days = cint(
        get_param(
            "tender_deadline_alert_days",
            3,
        )
    )

    owner = get_notification_owner(
        "sales_notification_owner"
    )

    current_date = getdate(today())
    active_references = []

    tenders = frappe.get_all(
        "PEPL Tender",
        fields=[
            "name",
            "customer",
            "status",
            "decision_date",
            "bid_decision",
        ],
        order_by="decision_date asc, name asc",
        limit_page_length=0,
    )

    for tender in tenders:
        if tender.status in TERMINAL_TENDER_STATUSES:
            continue

        if tender.bid_decision == "No Bid":
            continue

        if not tender.decision_date:
            continue

        days_remaining = date_diff(
            getdate(tender.decision_date),
            current_date,
        )

        if days_remaining > alert_days:
            continue

        active_references.append(tender.name)

        if days_remaining < 0:
            timing_text = "overdue by {0} day(s)".format(
                abs(days_remaining)
            )
            priority = "High"

        elif days_remaining == 0:
            timing_text = "due today"
            priority = "High"

        else:
            timing_text = "due in {0} day(s)".format(
                days_remaining
            )
            priority = (
                "High"
                if days_remaining <= 1
                else "Medium"
            )

        description = (
            "{marker}\n\n"
            "Tender {name} requires deadline attention.\n"
            "Customer: {customer}\n"
            "Status: {status}\n"
            "Decision Date: {decision_date}\n"
            "Deadline: {timing}"
        ).format(
            marker=_rule_marker(
                RULE_TENDER_DEADLINE
            ),
            name=tender.name,
            customer=tender.customer or "-",
            status=tender.status or "-",
            decision_date=tender.decision_date,
            timing=timing_text,
        )

        todo_result = upsert_operational_todo(
            rule_code=RULE_TENDER_DEADLINE,
            reference_type="PEPL Tender",
            reference_name=tender.name,
            allocated_to=owner,
            description=description,
            priority=priority,
            due_date=tender.decision_date,
        )

        _record_action(
            result,
            todo_result["action"],
        )

    result["closed"] = close_resolved_rule_todos(
        rule_code=RULE_TENDER_DEADLINE,
        reference_type="PEPL Tender",
        active_reference_names=active_references,
    )

    result["active"] = len(active_references)

    return result



def process_payment_ageing_exceptions():
    """Create, update, or close Payment ageing operational ToDos."""
    result = _empty_result()

    amber_days = cint(
        get_param(
            "payment_ageing_amber_days",
            60,
        )
    )
    red_days = cint(
        get_param(
            "payment_ageing_red_days",
            90,
        )
    )

    owner = get_notification_owner(
        "accounts_notification_owner"
    )

    active_references = []

    trackers = frappe.get_all(
        "PEPL Payment Tracker",
        filters={
            "payment_status": [
                "not in",
                list(CLOSED_PAYMENT_STATUSES),
            ],
            "total_outstanding": [">", 0],
            "days_outstanding": [
                ">=",
                amber_days,
            ],
        },
        fields=[
            "name",
            "linked_sales_invoice",
            "customer",
            "payment_status",
            "invoice_amount",
            "total_amount_received",
            "total_outstanding",
            "days_outstanding",
            "ageing_bucket",
        ],
        order_by=(
            "days_outstanding desc, name asc"
        ),
        limit_page_length=0,
    )

    for tracker in trackers:
        days = cint(
            tracker.days_outstanding
        )

        priority = (
            "High"
            if (
                days >= red_days
                or tracker.ageing_bucket
                == "45+ days (MSME breach)"
            )
            else "Medium"
        )

        invoice_label = (
            tracker.linked_sales_invoice
            or _("Not Linked")
        )

        description = (
            "{marker}\n\n"
            "Payment Tracker {name} requires ageing attention.\n"
            "Customer: {customer}\n"
            "Sales Invoice: {invoice}\n"
            "Payment Status: {status}\n"
            "Outstanding Amount: {outstanding}\n"
            "Days Outstanding: {days}\n"
            "Ageing Bucket: {bucket}"
        ).format(
            marker=_rule_marker(
                RULE_PAYMENT_AGEING
            ),
            name=tracker.name,
            customer=tracker.customer or "-",
            invoice=invoice_label,
            status=tracker.payment_status or "-",
            outstanding=frappe.format_value(
                tracker.total_outstanding,
                {
                    "fieldtype": "Currency",
                },
            ),
            days=days,
            bucket=tracker.ageing_bucket or "-",
        )

        active_references.append(
            tracker.name
        )

        todo_result = upsert_operational_todo(
            rule_code=RULE_PAYMENT_AGEING,
            reference_type=(
                "PEPL Payment Tracker"
            ),
            reference_name=tracker.name,
            allocated_to=owner,
            description=description,
            priority=priority,
            due_date=today(),
        )

        _record_action(
            result,
            todo_result["action"],
        )

    result["closed"] = (
        close_resolved_rule_todos(
            rule_code=RULE_PAYMENT_AGEING,
            reference_type=(
                "PEPL Payment Tracker"
            ),
            active_reference_names=(
                active_references
            ),
        )
    )

    result["active"] = len(
        active_references
    )

    return result



@frappe.whitelist()
def run_tender_deadline_notifications():
    """Controlled first-stage entry point for Tender deadline testing."""
    if not cint(
        get_param(
            "enable_operational_todos",
            0,
        )
    ):
        return {
            "enabled": False,
            "rule": RULE_TENDER_DEADLINE,
            **_empty_result(),
        }

    return {
        "enabled": True,
        "rule": RULE_TENDER_DEADLINE,
        **process_tender_deadline_exceptions(),
    }



@frappe.whitelist()
def run_payment_ageing_notifications():
    """Controlled entry point for Payment ageing UAT."""
    if not cint(
        get_param(
            "enable_operational_todos",
            0,
        )
    ):
        return {
            "enabled": False,
            "rule": RULE_PAYMENT_AGEING,
            **_empty_result(),
        }

    return {
        "enabled": True,
        "rule": RULE_PAYMENT_AGEING,
        **process_payment_ageing_exceptions(),
    }



@frappe.whitelist()
def run_daily_operational_notifications():
    """Daily entry point. Additional rules are enabled after UAT."""
    if not cint(
        get_param(
            "enable_operational_todos",
            0,
        )
    ):
        return {
            "enabled": False,
            "rules": {},
        }

    # Stage 1: Tender deadline only.
    return {
        "enabled": True,
        "rules": {
            "tender_deadline":
                process_tender_deadline_exceptions(),
        },
    }
