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




def process_document_pending_exceptions():
    """Create, update, or close pending-document operational ToDos."""
    result = _empty_result()

    alert_days = cint(
        get_param(
            "document_pending_alert_days",
            7,
        )
    )

    owner = get_notification_owner(
        "sales_notification_owner"
    )

    current_date = getdate(today())
    active_references = []

    trackers = frappe.get_all(
        "PEPL Document Tracker",
        fields=[
            "name",
            "linked_sales_order",
            "customer",
        ],
        order_by="name asc",
        limit_page_length=0,
    )

    for tracker in trackers:
        document = frappe.get_doc(
            "PEPL Document Tracker",
            tracker.name,
        )

        overdue_rows = []

        for row in document.document_entries or []:
            if not cint(row.is_required):
                continue

            if row.document_status != "Pending":
                continue

            base_date_value = (
                row.document_date
                or row.creation
            )

            if not base_date_value:
                continue

            base_date = getdate(
                base_date_value
            )

            age_days = date_diff(
                current_date,
                base_date,
            )

            if age_days < alert_days:
                continue

            overdue_rows.append({
                "name": row.name,
                "document_type": (
                    row.document_type
                    or _("Unspecified")
                ),
                "base_date": base_date,
                "age_days": age_days,
            })

        if not overdue_rows:
            continue

        overdue_rows.sort(
            key=lambda row: (
                -row["age_days"],
                row["document_type"],
                row["name"],
            )
        )

        marker = (
            "PEPL-OPS::"
            + RULE_DOCUMENT_PENDING
        )

        lines = [
            marker,
            "",
            _(
                "Document Tracker {0} has required "
                "documents pending beyond the "
                "configured alert window."
            ).format(tracker.name),
            _("Customer: {0}").format(
                tracker.customer or "-"
            ),
            _("Sales Order: {0}").format(
                tracker.linked_sales_order
                or _("Not Linked")
            ),
            _("Alert Window: {0} day(s)").format(
                alert_days
            ),
            _("Overdue Documents: {0}").format(
                len(overdue_rows)
            ),
            "",
        ]

        for row in overdue_rows:
            lines.append(
                "- {0}: pending for {1} day(s) "
                "since {2}".format(
                    row["document_type"],
                    row["age_days"],
                    row["base_date"],
                )
            )

        oldest_age = max(
            row["age_days"]
            for row in overdue_rows
        )

        priority = (
            "High"
            if oldest_age >= (
                alert_days * 2
            )
            else "Medium"
        )

        oldest_base_date = min(
            row["base_date"]
            for row in overdue_rows
        )

        description = "\n".join(lines)

        active_references.append(
            tracker.name
        )

        todo_result = upsert_operational_todo(
            rule_code=RULE_DOCUMENT_PENDING,
            reference_type=(
                "PEPL Document Tracker"
            ),
            reference_name=tracker.name,
            allocated_to=owner,
            priority=priority,
            description=description,
            due_date=oldest_base_date,
        )

        _record_action(
            result,
            todo_result["action"],
        )

    result["closed"] = (
        close_resolved_rule_todos(
            rule_code=RULE_DOCUMENT_PENDING,
            reference_type=(
                "PEPL Document Tracker"
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



def process_vendor_approval_exceptions():
    """Create, update, or close Vendor Approval operational ToDos."""
    result = _empty_result()

    owner = get_notification_owner(
        "engineering_notification_owner"
    )

    active_references = []

    approvals = frappe.get_all(
        "Vendor Approval Status",
        filters={
            "approval_health": [
                "in",
                [
                    "Expiring Soon",
                    "Expired",
                ],
            ],
        },
        fields=[
            "name",
            "customer",
            "item",
            "sector",
            "railways_stage",
            "defence_stage",
            "approval_health",
            "effective_expiry_date",
            "days_to_expiry",
            "approval_warning",
        ],
        order_by=(
            "effective_expiry_date asc, "
            "name asc"
        ),
        limit_page_length=0,
    )

    for approval in approvals:
        health = (
            approval.approval_health
            or ""
        )

        priority = (
            "High"
            if health == "Expired"
            else "Medium"
        )

        marker = (
            "PEPL-OPS::"
            + RULE_VENDOR_APPROVAL
        )

        expiry_label = (
            str(approval.effective_expiry_date)
            if approval.effective_expiry_date
            else _("Not Set")
        )

        warning = (
            approval.approval_warning
            or "-"
        )

        description = (
            marker
            + "\n\n"
            + _(
                "Vendor Approval {0} requires "
                "engineering attention."
            ).format(approval.name)
            + "\n"
            + _("Customer: {0}").format(
                approval.customer or "-"
            )
            + "\n"
            + _("Item: {0}").format(
                approval.item or "-"
            )
            + "\n"
            + _("Sector: {0}").format(
                approval.sector or "-"
            )
            + "\n"
            + _("Approval Stage: {0}").format(
                (
                    approval.railways_stage
                    if approval.sector == "Railways"
                    else approval.defence_stage
                    if approval.sector == "Defence"
                    else "-"
                )
                or "-"
            )
            + "\n"
            + _("Approval Health: {0}").format(
                health or "-"
            )
            + "\n"
            + _("Expiry Date: {0}").format(
                expiry_label
            )
            + "\n"
            + _("Days to Expiry: {0}").format(
                approval.days_to_expiry
                if (
                    approval.days_to_expiry
                    is not None
                )
                else "-"
            )
            + "\n"
            + _("Warning: {0}").format(
                warning
            )
        )

        active_references.append(
            approval.name
        )

        todo_result = upsert_operational_todo(
            rule_code=RULE_VENDOR_APPROVAL,
            reference_type=(
                "Vendor Approval Status"
            ),
            reference_name=approval.name,
            allocated_to=owner,
            priority=priority,
            description=description,
            due_date=(
                approval.effective_expiry_date
                or today()
            ),
        )

        _record_action(
            result,
            todo_result["action"],
        )

    result["closed"] = (
        close_resolved_rule_todos(
            rule_code=RULE_VENDOR_APPROVAL,
            reference_type=(
                "Vendor Approval Status"
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




def process_psd_expiry_exceptions():
    """Create, update, or close PSD expiry operational ToDos."""
    result = _empty_result()

    alert_days = cint(
        get_param(
            "psd_expiry_alert_days",
            30,
        )
    )

    owner = get_notification_owner(
        "accounts_notification_owner"
    )

    today_date = getdate(today())

    cutoff_date = frappe.utils.add_days(
        today_date,
        alert_days,
    )

    submissions = frappe.get_all(
        "PEPL PSD Submission",
        filters={
            "parenttype": "PEPL PSD Tracker",
            "parentfield": "psd_submissions",
            "is_active": 1,
            "validity_date": [
                "<=",
                cutoff_date,
            ],
        },
        fields=[
            "name",
            "parent",
            "psd_entry_label",
            "instrument_type",
            "reference_number",
            "issuing_bank",
            "issue_date",
            "validity_date",
            "renewal_of",
        ],
        order_by=(
            "parent asc, "
            "validity_date asc, "
            "name asc"
        ),
        limit_page_length=0,
    )

    grouped = {}

    for submission in submissions:
        grouped.setdefault(
            submission.parent,
            [],
        ).append(submission)

    active_references = []

    marker = (
        "PEPL-OPS::"
        + RULE_PSD_EXPIRY
    )

    for tracker_name in sorted(grouped):
        tracker = frappe.db.get_value(
            "PEPL PSD Tracker",
            tracker_name,
            [
                "linked_sales_order",
                "customer",
                "sector",
            ],
            as_dict=True,
        )

        if not tracker:
            continue

        tracker_submissions = grouped[
            tracker_name
        ]

        earliest_validity = min(
            getdate(row.validity_date)
            for row in tracker_submissions
            if row.validity_date
        )

        has_expired = any(
            getdate(row.validity_date)
            < today_date
            for row in tracker_submissions
            if row.validity_date
        )

        priority = (
            "High"
            if has_expired
            else "Medium"
        )

        lines = []

        for row in tracker_submissions:
            validity_date = getdate(
                row.validity_date
            )

            days_to_expiry = date_diff(
                validity_date,
                today_date,
            )

            if days_to_expiry < 0:
                timing = _(
                    "expired {0} day(s) ago"
                ).format(
                    abs(days_to_expiry)
                )
            elif days_to_expiry == 0:
                timing = _("expires today")
            else:
                timing = _(
                    "expires in {0} day(s)"
                ).format(
                    days_to_expiry
                )

            instrument_label = (
                row.instrument_type
                or _("Instrument")
            )

            if row.reference_number:
                instrument_label += (
                    " "
                    + row.reference_number
                )

            line = (
                "- "
                + instrument_label
                + ": "
                + timing
                + " on "
                + str(validity_date)
            )

            if row.issuing_bank:
                line += (
                    " | Bank: "
                    + row.issuing_bank
                )

            if row.psd_entry_label:
                line += (
                    " | PSD Entry: "
                    + row.psd_entry_label
                )

            lines.append(line)

        description = (
            marker
            + "\n\n"
            + _(
                "PSD Tracker {0} has active "
                "instrument(s) expired or expiring "
                "within the configured alert window."
            ).format(tracker_name)
            + "\n"
            + _("Customer: {0}").format(
                tracker.customer or "-"
            )
            + "\n"
            + _("Sales Order: {0}").format(
                tracker.linked_sales_order or "-"
            )
            + "\n"
            + _("Sector: {0}").format(
                tracker.sector or "-"
            )
            + "\n"
            + _("Alert Window: {0} day(s)").format(
                alert_days
            )
            + "\n"
            + _("Affected Instruments: {0}").format(
                len(tracker_submissions)
            )
            + "\n\n"
            + "\n".join(lines)
        )

        active_references.append(
            tracker_name
        )

        todo_result = upsert_operational_todo(
            rule_code=RULE_PSD_EXPIRY,
            reference_type=(
                "PEPL PSD Tracker"
            ),
            reference_name=tracker_name,
            allocated_to=owner,
            priority=priority,
            description=description,
            due_date=earliest_validity,
        )

        _record_action(
            result,
            todo_result["action"],
        )

    result["closed"] = (
        close_resolved_rule_todos(
            rule_code=RULE_PSD_EXPIRY,
            reference_type=(
                "PEPL PSD Tracker"
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
def run_vendor_approval_notifications():
    """Controlled entry point for Vendor Approval UAT."""
    if not cint(
        get_param(
            "enable_operational_todos",
            0,
        )
    ):
        return {
            "enabled": False,
            "rule": RULE_VENDOR_APPROVAL,
            **_empty_result(),
        }

    return {
        "enabled": True,
        "rule": RULE_VENDOR_APPROVAL,
        **process_vendor_approval_exceptions(),
    }



@frappe.whitelist()
def run_vendor_approval_refresh_and_notifications():
    """Refresh Vendor Approval health, then synchronize ToDos."""
    from pepl_sales.pepl_sales.doctype.vendor_approval_status.vendor_approval_status import (
        refresh_all_vendor_approval_health,
    )

    refresh_result = (
        refresh_all_vendor_approval_health()
    )

    notification_result = (
        run_vendor_approval_notifications()
    )

    return {
        "refresh": refresh_result,
        "notifications": notification_result,
    }



@frappe.whitelist()
def run_document_pending_notifications():
    """Controlled entry point for pending-document UAT."""
    if not cint(
        get_param(
            "enable_operational_todos",
            0,
        )
    ):
        return {
            "enabled": False,
            "rule": RULE_DOCUMENT_PENDING,
            **_empty_result(),
        }

    return {
        "enabled": True,
        "rule": RULE_DOCUMENT_PENDING,
        **process_document_pending_exceptions(),
    }




@frappe.whitelist()
def run_psd_expiry_notifications():
    """Controlled entry point for PSD expiry UAT."""
    if not cint(
        get_param(
            "enable_operational_todos",
            0,
        )
    ):
        return {
            "enabled": False,
            "rule": RULE_PSD_EXPIRY,
            **_empty_result(),
        }

    return {
        "enabled": True,
        "rule": RULE_PSD_EXPIRY,
        **process_psd_expiry_exceptions(),
    }




def process_psd_refund_exceptions():
    """Create, update, or close overdue PSD Refund operational ToDos."""
    result = _empty_result()

    owner = get_notification_owner(
        "accounts_notification_owner"
    )

    current_date = getdate(today())
    active_references = []
    grouped_entries = {}

    entries = frappe.get_all(
        "PEPL PSD Entry",
        filters={
            "parenttype": "PEPL PSD Tracker",
            "parentfield": "psd_entries",
            "expected_refund_date": [
                "<=",
                current_date,
            ],
            "psd_amount": [
                ">",
                0,
            ],
            "psd_status": [
                "not in",
                list(CLOSED_PSD_STATUSES),
            ],
            "psd_refund_date": [
                "is",
                "not set",
            ],
        },
        fields=[
            "name",
            "parent",
            "entry_label",
            "psd_status",
            "psd_amount",
            "last_supply_date",
            "expected_refund_date",
            "ndc_requested_date",
            "ndc_received_date",
            "letter_to_bank_date",
        ],
        order_by=(
            "expected_refund_date asc, "
            "parent asc, "
            "name asc"
        ),
        limit_page_length=0,
    )

    for entry in entries:
        if not entry.parent:
            continue

        if not entry.expected_refund_date:
            continue

        grouped_entries.setdefault(
            entry.parent,
            [],
        ).append(entry)

    for tracker_name, tracker_entries in (
        grouped_entries.items()
    ):
        tracker = frappe.db.get_value(
            "PEPL PSD Tracker",
            tracker_name,
            [
                "name",
                "customer",
                "linked_sales_order",
                "sector",
            ],
            as_dict=True,
        )

        if not tracker:
            continue

        active_references.append(
            tracker_name
        )

        valid_entries = [
            entry
            for entry in tracker_entries
            if entry.expected_refund_date
        ]

        if not valid_entries:
            continue

        refund_dates = [
            getdate(
                entry.expected_refund_date
            )
            for entry in valid_entries
        ]

        earliest_refund_date = min(
            refund_dates
        )

        maximum_days_overdue = max(
            date_diff(
                current_date,
                refund_date,
            )
            for refund_date in refund_dates
        )

        priority = (
            "High"
            if maximum_days_overdue >= 30
            else "Medium"
        )

        lines = []

        for entry in valid_entries:
            refund_date = getdate(
                entry.expected_refund_date
            )

            days_overdue = date_diff(
                current_date,
                refund_date,
            )

            lines.append(
                "- {0}: ₹ {1:,.2f} overdue by "
                "{2} day(s) since {3} | "
                "Status: {4} | "
                "NDC Requested: {5} | "
                "NDC Received: {6} | "
                "Letter to Bank: {7}".format(
                    entry.entry_label or entry.name,
                    flt(entry.psd_amount),
                    days_overdue,
                    refund_date,
                    entry.psd_status or "-",
                    entry.ndc_requested_date or "-",
                    entry.ndc_received_date or "-",
                    entry.letter_to_bank_date or "-",
                )
            )

        description = (
            _(
                "PSD Tracker {0} has PSD refund "
                "amount(s) due or overdue."
            ).format(
                tracker_name
            )
            + "\n"
            + _("Customer: {0}").format(
                tracker.customer or "-"
            )
            + "\n"
            + _("Sales Order: {0}").format(
                tracker.linked_sales_order or "-"
            )
            + "\n"
            + _("Sector: {0}").format(
                tracker.sector or "-"
            )
            + "\n"
            + _("Affected PSD Entries: {0}").format(
                len(valid_entries)
            )
            + "\n"
            + _("Maximum Days Overdue: {0}").format(
                maximum_days_overdue
            )
            + "\n\n"
            + "\n".join(lines)
        )

        todo_result = upsert_operational_todo(
            rule_code=RULE_PSD_REFUND,
            reference_type="PEPL PSD Tracker",
            reference_name=tracker_name,
            allocated_to=owner,
            description=description,
            priority=priority,
            due_date=earliest_refund_date,
        )

        action = todo_result.get(
            "action"
        )

        if action in result:
            result[action] += 1

    result["closed"] = (
        close_resolved_rule_todos(
            rule_code=RULE_PSD_REFUND,
            reference_type="PEPL PSD Tracker",
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
def run_psd_refund_notifications():
    """Controlled entry point for PSD Refund notifications."""
    if not cint(
        get_param(
            "enable_operational_todos",
            0,
        )
    ):
        return {
            "enabled": False,
            "rule": RULE_PSD_REFUND,
            **_empty_result(),
        }

    return {
        "enabled": True,
        "rule": RULE_PSD_REFUND,
        **process_psd_refund_exceptions(),
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
