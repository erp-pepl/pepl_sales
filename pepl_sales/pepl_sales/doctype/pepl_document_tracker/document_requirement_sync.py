from __future__ import annotations

import frappe
from frappe.utils import now_datetime


PILOT_SOURCE_TRANSACTION = "Sales Order"
PILOT_BUSINESS_STAGES = [
    "Engineering Documents",
]


def get_document_requirements(
    *,
    sector,
    source_transaction,
    business_stages,
):
    """Return active Common and sector-specific requirements."""
    valid_sectors = ["Common"]

    if sector and sector != "Common":
        valid_sectors.append(sector)

    return frappe.get_all(
        "PEPL Document Requirement",
        filters={
            "active": 1,
            "sector": ["in", valid_sectors],
            "source_transaction": source_transaction,
            "business_stage": [
                "in",
                business_stages,
            ],
        },
        fields=[
            "name",
            "document_code",
            "document_name",
            "sector",
            "business_stage",
            "source_transaction",
            "document_category",
            "mandatory",
            "evidence_required",
            "generated_by_pepl",
            "external_issued",
            "allow_multiple",
            "blocking_event",
            "sequence",
        ],
        order_by=(
            "sequence asc, document_code asc"
        ),
        limit_page_length=1000,
    )


def synchronize_engineering_requirements(
    tracker,
    sales_order,
    sector,
):
    """Synchronize the non-blocking Engineering pilot.

    Manual and legacy rows are never converted, deleted or
    overwritten. Only rows carrying a requirement link/code
    are managed by this function.
    """
    requirements = get_document_requirements(
        sector=sector,
        source_transaction=(
            PILOT_SOURCE_TRANSACTION
        ),
        business_stages=PILOT_BUSINESS_STAGES,
    )

    requirement_by_name = {
        row.name: row
        for row in requirements
    }

    managed_rows = {}

    for row in tracker.document_entries or []:
        key = (
            row.get("requirement")
            or row.get("requirement_code")
        )

        if not key:
            continue

        if key not in managed_rows:
            managed_rows[key] = row
            continue

        # Preserve accidental duplicate evidence but remove
        # duplicate rows from the active managed checklist.
        row.is_active_requirement = 0
        row.is_historical = 1

        if row.document_status == "Pending":
            row.document_status = "Obsolete"

    now = now_datetime()
    current_user = (
        frappe.session.user
        or "Administrator"
    )

    created = 0
    updated = 0
    historical = 0

    for requirement in requirements:
        row = managed_rows.get(
            requirement.name
        )

        if not row:
            row = tracker.append(
                "document_entries",
                {}
            )

            managed_rows[requirement.name] = row
            created += 1
        else:
            updated += 1

        row.requirement = requirement.name
        row.requirement_code = (
            requirement.document_code
        )
        row.business_stage = (
            requirement.business_stage
        )
        row.document_category = (
            requirement.document_category
        )
        row.requirement_source_transaction = (
            requirement.source_transaction
        )

        row.is_managed_requirement = 1
        row.is_active_requirement = 1
        row.is_historical = 0

        row.generated_by_pepl = (
            requirement.generated_by_pepl
        )
        row.external_issued = (
            requirement.external_issued
        )
        row.evidence_required = (
            requirement.evidence_required
        )
        row.allow_multiple = (
            requirement.allow_multiple
        )
        row.blocking_event = (
            requirement.blocking_event
            or "None"
        )

        row.last_synced_on = now
        row.last_synced_by = current_user

        row.document_type = (
            requirement.document_name
        )

        if not row.description:
            row.description = (
                requirement.document_name
                + " — configured requirement"
            )

        if not row.document_status:
            row.document_status = "Pending"

        if requirement.external_issued:
            row.direction = (
                "Inbound (from Customer)"
            )
        elif requirement.generated_by_pepl:
            row.direction = (
                "Outbound (to Customer)"
            )
        elif not row.direction:
            row.direction = "Internal"

        row.source = (
            "Auto-Generated from Requirement"
        )
        row.source_reference = (
            sales_order.name
        )

        # All current seed records are non-mandatory.
        # Copying the master value preserves future UAT changes
        # without activating blocking behavior.
        row.is_required = int(
            requirement.mandatory or 0
        )

    for key, row in managed_rows.items():
        if key in requirement_by_name:
            continue

        # Only retire rows managed by this same pilot.
        if (
            row.get(
                "requirement_source_transaction"
            )
            != PILOT_SOURCE_TRANSACTION
            or row.get("business_stage")
            not in PILOT_BUSINESS_STAGES
        ):
            continue

        if row.is_active_requirement:
            historical += 1

        row.is_active_requirement = 0
        row.is_historical = 1
        row.last_synced_on = now
        row.last_synced_by = current_user

        if row.document_status == "Pending":
            row.document_status = "Obsolete"

    return {
        "created": created,
        "updated": updated,
        "historical": historical,
        "requirements": len(requirements),
        "requirement_codes": [
            row.document_code
            for row in requirements
        ],
    }
