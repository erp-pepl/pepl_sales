from __future__ import annotations

import frappe
from frappe.utils import getdate, now_datetime, today


STAGE_MAP = {
    "Railways": {
        "Unapproved": "Applied",
        "Applied": "Applied",
        "Developmental": "Developmental",
        "Approved": "Approved",
    },
    "Defence": {
        "Source Development": "Developmental",
        "Developmental": "Developmental",
        "Approved / Established": "Established",
        "Established": "Established",
    },
}

STAGE_SEQUENCE = {
    "Railways": [
        "Applied",
        "Developmental",
        "Approved",
    ],
    "Defence": [
        "Developmental",
        "Established",
    ],
}

DOCUMENT_TYPE_MAP = {
    "PAN": "PAN Card",
    "Udyam Registration": "Udyam Aadhaar",
    "Approved Drawing": "Item Drawing",
    "Approved Specification": "Item Specification",
}


def normalize_stage_value(sector, stage):
    if not sector or not stage:
        return None

    return STAGE_MAP.get(sector, {}).get(stage)


def get_normalized_stage(doc):
    if doc.sector == "Railways":
        stage = doc.railways_stage
    elif doc.sector == "Defence":
        stage = doc.defence_stage
    else:
        stage = None

    return normalize_stage_value(doc.sector, stage)


def get_applicable_stages(sector, normalized_stage):
    sequence = STAGE_SEQUENCE.get(sector, [])

    if normalized_stage not in sequence:
        return []

    return sequence[: sequence.index(normalized_stage) + 1]


def get_requirement_records(sector, stage):
    normalized_stage = normalize_stage_value(sector, stage) or stage
    applicable_stages = get_applicable_stages(
        sector,
        normalized_stage,
    )

    if not sector or not applicable_stages:
        return []

    return frappe.get_all(
        "PEPL Vendor Approval Requirement",
        filters={
            "active": 1,
            "sector": ["in", [sector, "Common"]],
            "approval_stage": ["in", applicable_stages],
        },
        fields=[
            "name",
            "requirement_code",
            "requirement_name",
            "sector",
            "approval_stage",
            "document_category",
            "document_name",
            "mandatory",
            "auto_fetch_source",
            "item_specific",
            "sales_order_specific",
            "validity_required",
            "sequence",
        ],
        order_by="approval_stage asc, sequence asc, name asc",
        limit_page_length=1000,
    )


def get_required_document_names(sector, stage):
    requirements = get_requirement_records(
        sector,
        stage,
    )

    return [
        requirement.document_name
        for requirement in requirements
    ]


def _row_has_evidence(row):
    return bool(
        row.file_attach
        or row.linked_company_document
        or row.linked_drawing_revision
        or row.linked_specification
    )



COMPANY_DOCUMENT_TYPE_MAP = {
    "PAN": "PAN Card",
    "Udyam Registration": "Udyam Aadhaar",
}


def _is_expired(expiry_date):
    return bool(
        expiry_date
        and getdate(expiry_date) < getdate(today())
    )


def _get_company_document_candidate(document_type):
    """Return the best active Company Document source.

    Selection priority:
    1. Active records only
    2. Current file and issue date required
    3. Non-expired record preferred
    4. Latest issue date
    5. Latest modified timestamp
    6. Stable name tie-breaker
    """
    if not document_type:
        return None

    candidates = frappe.get_all(
        "PEPL Company Document",
        filters={
            "document_type": document_type,
            "is_active": 1,
        },
        fields=[
            "name",
            "document_type",
            "current_version_number",
            "current_version_file",
            "current_issue_date",
            "current_expiry_date",
            "current_reference_no",
            "modified",
        ],
        order_by=(
            "current_issue_date desc, "
            "modified desc, name asc"
        ),
        limit_page_length=100,
    )

    usable = []

    for candidate in candidates:
        if not candidate.current_version_file:
            continue

        if not candidate.current_issue_date:
            continue

        usable.append(candidate)

    if not usable:
        return None

    non_expired = [
        candidate
        for candidate in usable
        if not _is_expired(
            candidate.current_expiry_date
        )
    ]

    if non_expired:
        return non_expired[0]

    return usable[0]


def _has_manual_upload(row):
    """Protect manual evidence from automatic replacement."""
    return bool(
        row.document_source == "Upload File"
        and row.file_attach
        and not row.linked_company_document
    )


def _clear_company_source_metadata(row):
    row.linked_company_document = None
    row.source_record_doctype = None
    row.source_record_name = None
    row.source_version = None


def _apply_company_document_source(row, requirement):
    """Populate one synchronized row from Company Document.

    Returns:
        "manual-preserved"
        "available"
        "expired"
        "pending"
        "not-applicable"
    """
    source_type = COMPANY_DOCUMENT_TYPE_MAP.get(
        requirement.document_name
    )

    is_company_requirement = bool(
        source_type
        and (
            requirement.auto_fetch_source
            == "PEPL Company Document"
            or requirement.document_category
            == "Company Document"
        )
    )

    if not is_company_requirement:
        return "not-applicable"

    if _has_manual_upload(row):
        return "manual-preserved"

    candidate = _get_company_document_candidate(
        source_type
    )

    if not candidate:
        if row.document_source == "Company Library":
            _clear_company_source_metadata(row)

        if not row.file_attach:
            row.document_source = "Upload File"

        row.requirement_status = "Pending"
        return "pending"

    row.document_source = "Company Library"
    row.document_type = source_type
    row.linked_company_document = candidate.name
    row.file_attach = candidate.current_version_file
    row.issue_date = candidate.current_issue_date
    row.expiry_date = candidate.current_expiry_date
    row.reference_no = candidate.current_reference_no

    row.source_record_doctype = (
        "PEPL Company Document"
    )
    row.source_record_name = candidate.name
    row.source_version = (
        candidate.current_version_number
    )

    if _is_expired(candidate.current_expiry_date):
        row.requirement_status = "Expired"
        return "expired"

    row.requirement_status = "Available"
    return "available"

def _set_requirement_status(row):
    if row.is_historical:
        row.requirement_status = "Superseded"
        return

    if row.expiry_date:
        if getdate(row.expiry_date) < getdate(today()):
            row.requirement_status = "Expired"
            return

    if _row_has_evidence(row):
        row.requirement_status = "Available"
    else:
        row.requirement_status = "Pending"


def _document_type_for_requirement(requirement):
    return DOCUMENT_TYPE_MAP.get(
        requirement.document_name,
        (
            requirement.document_name
            if requirement.document_name
            else "Other"
        ),
    )


def _new_requirement_row(doc, requirement):
    row = doc.append(
        "vendor_approval_documents",
        {},
    )

    # Commit 1 creates the controlled requirement row only.
    # Actual Company/Product source retrieval is implemented
    # in later commits.
    row.document_source = "Upload File"
    row.document_type = _document_type_for_requirement(
        requirement
    )
    row.document_name = requirement.document_name

    return row


def synchronize_requirement_rows(doc):
    normalized_stage = get_normalized_stage(doc)
    doc.normalized_approval_stage = normalized_stage

    if not doc.sector or not normalized_stage:
        doc.requirement_sync_status = "Needs Review"
        doc.pending_mandatory_documents = 0
        doc.approval_documents_complete = 0
        return {
            "created": 0,
            "updated": 0,
            "historical": 0,
            "requirements": 0,
        }

    requirements = get_requirement_records(
        doc.sector,
        normalized_stage,
    )

    requirement_by_code = {
        requirement.name: requirement
        for requirement in requirements
    }

    managed_rows = {}

    for row in doc.vendor_approval_documents or []:
        if not row.requirement_code:
            continue

        if row.requirement_code not in managed_rows:
            managed_rows[row.requirement_code] = row
        else:
            # Preserve duplicate historical evidence but remove it
            # from the active synchronized set.
            row.is_active_requirement = 0
            row.is_historical = 1
            row.requirement_status = "Superseded"

    now = now_datetime()
    current_user = frappe.session.user or "Administrator"

    created = 0
    updated = 0
    historical = 0

    for requirement_code, requirement in requirement_by_code.items():
        row = managed_rows.get(requirement_code)

        if not row:
            row = _new_requirement_row(
                doc,
                requirement,
            )
            managed_rows[requirement_code] = row
            created += 1
        else:
            updated += 1

        row.requirement_code = requirement.name
        row.requirement_stage = requirement.approval_stage
        row.requirement_category = (
            requirement.document_category
        )
        row.is_mandatory = requirement.mandatory
        row.is_auto_generated = 1
        row.is_active_requirement = 1
        row.is_historical = 0
        row.sync_key = requirement.name
        row.last_synced_on = now
        row.last_synced_by = current_user

        if not row.document_name:
            row.document_name = requirement.document_name

        if not row.document_type:
            row.document_type = (
                _document_type_for_requirement(requirement)
            )

        company_source_result = (
            _apply_company_document_source(
                row,
                requirement,
            )
        )

        if company_source_result in [
            "not-applicable",
            "manual-preserved",
        ]:
            _set_requirement_status(row)

    for requirement_code, row in managed_rows.items():
        if requirement_code in requirement_by_code:
            continue

        if not row.is_historical:
            historical += 1

        row.is_active_requirement = 0
        row.is_historical = 1
        row.requirement_status = "Superseded"
        row.last_synced_on = now
        row.last_synced_by = current_user

    pending_mandatory = 0

    for row in doc.vendor_approval_documents or []:
        if not row.requirement_code:
            continue

        if not row.is_active_requirement:
            continue

        _set_requirement_status(row)

        if (
            row.is_mandatory
            and row.requirement_status != "Available"
        ):
            pending_mandatory += 1

    doc.pending_mandatory_documents = pending_mandatory
    doc.approval_documents_complete = int(
        bool(requirements)
        and pending_mandatory == 0
    )
    doc.requirement_sync_status = (
        "Synced"
        if requirements
        else "Needs Review"
    )
    doc.requirements_last_synced_on = now
    doc.requirements_last_synced_by = current_user

    return {
        "created": created,
        "updated": updated,
        "historical": historical,
        "requirements": len(requirements),
        "pending_mandatory": pending_mandatory,
        "normalized_stage": normalized_stage,
    }
