from __future__ import annotations

import frappe
from frappe.utils import now_datetime


SALES_ORDER_SOURCE_TRANSACTION = "Sales Order"

ENGINEERING_BUSINESS_STAGES = [
    "Engineering Documents",
]

ACTIVE_SALES_ORDER_STAGES = [
    "Engineering Documents",
    "Raw Material Inspection",
    "NABL Testing",
    "Lot Formation",
    "Bulk Inspection",
    "Pre-Dispatch",
    "Dispatch",
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



def _find_adoptable_legacy_row(
    tracker,
    requirement,
):
    """Return a safe legacy row for managed adoption.

    MATERIAL_RECEIPT must reuse the existing operational
    Material Receipt row so previously uploaded evidence and
    the attachment validation workflow remain intact.
    """

    if (
        requirement.document_code
        != "MATERIAL_RECEIPT"
    ):
        return None

    candidates = []

    for row in tracker.document_entries or []:
        if (
            row.document_type
            == "Material Receipt"
            and not row.get("requirement")
            and not row.get("requirement_code")
            and not row.get(
                "is_managed_requirement"
            )
        ):
            candidates.append(row)

    if len(candidates) > 1:
        frappe.throw(
            "Document Tracker {0} contains multiple "
            "legacy Material Receipt rows. Resolve the "
            "duplicate rows before synchronization."
            .format(tracker.name)
        )

    if len(candidates) == 1:
        return candidates[0]

    return None


def _synchronize_requirements(
    *,
    tracker,
    source_document,
    sector,
    source_transaction,
    business_stages,
):
    """Synchronize managed requirements without changing legacy rows.

    Rows without requirement metadata are treated as legacy or manual
    rows and remain untouched.

    Existing managed rows preserve their evidence, status, dates,
    references and attachments.
    """
    requirements = get_document_requirements(
        sector=sector,
        source_transaction=source_transaction,
        business_stages=business_stages,
    )

    requirement_by_name = {
        requirement.name: requirement
        for requirement in requirements
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

        # Preserve accidental duplicate evidence, but remove the
        # duplicate from the active managed checklist.
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
    adopted = 0
    updated = 0
    historical = 0
    created_codes = []

    for requirement in requirements:
        row = managed_rows.get(
            requirement.name
        )

        was_adopted = False

        if not row:
            row = _find_adoptable_legacy_row(
                tracker,
                requirement,
            )

            if row:
                was_adopted = True
                adopted += 1
            else:
                row = tracker.append(
                    "document_entries",
                    {},
                )

                created += 1
                created_codes.append(
                    requirement.document_code
                )

            managed_rows[requirement.name] = row
        else:
            updated += 1

        # Synchronization metadata.
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

        # Update configured identity while preserving operational
        # evidence and completion state.
        if (
            requirement.document_code
            == "MATERIAL_RECEIPT"
        ):
            # Preserve the operational document type permanently.
            # PEPLDocumentTracker validates receipt evidence using
            # the exact legacy value "Material Receipt".
            row.document_type = "Material Receipt"
        else:
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
            source_document.name
        )

        # Master values currently remain optional and non-blocking.
        row.is_required = int(
            requirement.mandatory or 0
        )

    for key, row in managed_rows.items():
        if key in requirement_by_name:
            continue

        # Only retire rows controlled by this synchronization scope.
        if (
            row.get(
                "requirement_source_transaction"
            )
            != source_transaction
            or row.get("business_stage")
            not in business_stages
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
        "adopted": adopted,
        "updated": updated,
        "historical": historical,
        "requirements": len(requirements),
        "created_codes": created_codes,
        "requirement_codes": [
            requirement.document_code
            for requirement in requirements
        ],
    }


def synchronize_sales_order_requirements(
    tracker,
    sales_order,
    sector,
):
    """Synchronize approved non-blocking Sales Order stages.

    Dispatch is included. MATERIAL_RECEIPT safely adopts the
    existing legacy Material Receipt row whenever one exists.
    """
    return _synchronize_requirements(
        tracker=tracker,
        source_document=sales_order,
        sector=sector,
        source_transaction=(
            SALES_ORDER_SOURCE_TRANSACTION
        ),
        business_stages=(
            ACTIVE_SALES_ORDER_STAGES
        ),
    )


def synchronize_engineering_requirements(
    tracker,
    sales_order,
    sector,
):
    """Backward-compatible Engineering-only synchronization.

    This function must remain available because the previously
    deployed Engineering migration patch imports it. New application
    logic should use synchronize_sales_order_requirements().
    """
    return _synchronize_requirements(
        tracker=tracker,
        source_document=sales_order,
        sector=sector,
        source_transaction=(
            SALES_ORDER_SOURCE_TRANSACTION
        ),
        business_stages=(
            ENGINEERING_BUSINESS_STAGES
        ),
    )
