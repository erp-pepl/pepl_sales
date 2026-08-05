from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from pepl_sales.document_tracker_validation import (
    validate_document_tracker,
)
from pepl_sales.pepl_sales.doctype.pepl_document_tracker.document_requirement_sync import (
    _synchronize_requirements,
)


class FakeRow:
    def __init__(self, **values):
        self.__dict__.update(values)

    def get(self, key, default=None):
        return getattr(
            self,
            key,
            default,
        )


class FakeTracker:
    def __init__(self, rows=None):
        self.name = "TEST-TRACKER"
        self.document_entries = (
            rows or []
        )

    def append(
        self,
        fieldname,
        values,
    ):
        row = FakeRow(
            idx=(
                len(
                    self.document_entries
                )
                + 1
            ),
            requirement=None,
            requirement_code=None,
            business_stage=None,
            document_category=None,
            requirement_source_transaction=None,
            is_managed_requirement=0,
            is_active_requirement=0,
            is_historical=0,
            generated_by_pepl=0,
            external_issued=0,
            evidence_required=0,
            allow_multiple=0,
            blocking_event="None",
            last_synced_on=None,
            last_synced_by=None,
            document_type=None,
            description=None,
            document_status="Pending",
            direction=None,
            source=None,
            source_reference=None,
            is_required=0,
            receipt_attachment=None,
            received_date=None,
            received_by=None,
        )

        self.document_entries.append(
            row
        )

        return row


class TestDocumentRequirementSync(
    FrappeTestCase
):
    def _requirement(
        self,
        name,
        document_code,
        document_name,
    ):
        return SimpleNamespace(
            name=name,
            document_code=document_code,
            document_name=document_name,
            sector="Common",
            business_stage="Sales Invoice",
            source_transaction="Sales Invoice",
            document_category="Invoice",
            mandatory=0,
            evidence_required=0,
            generated_by_pepl=1,
            external_issued=0,
            allow_multiple=0,
            blocking_event="None",
            sequence=1,
        )

    @patch(
        "pepl_sales.pepl_sales.doctype."
        "pepl_document_tracker."
        "document_requirement_sync."
        "get_document_requirements"
    )
    def test_invoice_sync_is_idempotent(
        self,
        get_requirements,
    ):
        get_requirements.return_value = [
            self._requirement(
                "GST_SUMMARY",
                "GST_SUMMARY",
                "GST Summary",
            )
        ]

        tracker = FakeTracker()
        invoice = SimpleNamespace(
            name="SINV-TEST-0001"
        )

        first = _synchronize_requirements(
            tracker=tracker,
            source_document=invoice,
            sector="Railways",
            source_transaction=(
                "Sales Invoice"
            ),
            business_stages=[
                "Sales Invoice",
            ],
        )

        second = _synchronize_requirements(
            tracker=tracker,
            source_document=invoice,
            sector="Railways",
            source_transaction=(
                "Sales Invoice"
            ),
            business_stages=[
                "Sales Invoice",
            ],
        )

        self.assertEqual(
            first["created"],
            1,
        )

        self.assertEqual(
            second["created"],
            0,
        )

        self.assertEqual(
            len(
                tracker.document_entries
            ),
            1,
        )

    @patch(
        "pepl_sales.pepl_sales.doctype."
        "pepl_document_tracker."
        "document_requirement_sync."
        "get_document_requirements"
    )
    def test_two_invoices_get_separate_rows(
        self,
        get_requirements,
    ):
        get_requirements.return_value = [
            self._requirement(
                "GST_SUMMARY",
                "GST_SUMMARY",
                "GST Summary",
            )
        ]

        tracker = FakeTracker()

        _synchronize_requirements(
            tracker=tracker,
            source_document=(
                SimpleNamespace(
                    name="SINV-TEST-0001"
                )
            ),
            sector="Railways",
            source_transaction=(
                "Sales Invoice"
            ),
            business_stages=[
                "Sales Invoice",
            ],
        )

        _synchronize_requirements(
            tracker=tracker,
            source_document=(
                SimpleNamespace(
                    name="SINV-TEST-0002"
                )
            ),
            sector="Railways",
            source_transaction=(
                "Sales Invoice"
            ),
            business_stages=[
                "Sales Invoice",
            ],
        )

        self.assertEqual(
            len(
                tracker.document_entries
            ),
            2,
        )

        references = {
            row.source_reference
            for row in (
                tracker.document_entries
            )
        }

        self.assertEqual(
            references,
            {
                "SINV-TEST-0001",
                "SINV-TEST-0002",
            },
        )

    def test_validation_allows_same_type_for_two_invoices(
        self,
    ):
        rows = [
            FakeRow(
                idx=1,
                document_type="GST Summary",
                document_status="Pending",
                is_managed_requirement=1,
                requirement="GST_SUMMARY",
                requirement_code="GST_SUMMARY",
                requirement_source_transaction=(
                    "Sales Invoice"
                ),
                source_reference=(
                    "SINV-TEST-0001"
                ),
                receipt_attachment=None,
                received_date=None,
                received_by=None,
            ),
            FakeRow(
                idx=2,
                document_type="GST Summary",
                document_status="Pending",
                is_managed_requirement=1,
                requirement="GST_SUMMARY",
                requirement_code="GST_SUMMARY",
                requirement_source_transaction=(
                    "Sales Invoice"
                ),
                source_reference=(
                    "SINV-TEST-0002"
                ),
                receipt_attachment=None,
                received_date=None,
                received_by=None,
            ),
        ]

        tracker = FakeTracker(rows)

        validate_document_tracker(
            tracker
        )

    def test_validation_rejects_duplicate_invoice_requirement(
        self,
    ):
        rows = [
            FakeRow(
                idx=1,
                document_type="GST Summary",
                document_status="Pending",
                is_managed_requirement=1,
                requirement="GST_SUMMARY",
                requirement_code="GST_SUMMARY",
                requirement_source_transaction=(
                    "Sales Invoice"
                ),
                source_reference=(
                    "SINV-TEST-0001"
                ),
                receipt_attachment=None,
                received_date=None,
                received_by=None,
            ),
            FakeRow(
                idx=2,
                document_type="GST Summary",
                document_status="Pending",
                is_managed_requirement=1,
                requirement="GST_SUMMARY",
                requirement_code="GST_SUMMARY",
                requirement_source_transaction=(
                    "Sales Invoice"
                ),
                source_reference=(
                    "SINV-TEST-0001"
                ),
                receipt_attachment=None,
                received_date=None,
                received_by=None,
            ),
        ]

        tracker = FakeTracker(rows)

        with self.assertRaises(
            frappe.ValidationError
        ):
            validate_document_tracker(
                tracker
            )
