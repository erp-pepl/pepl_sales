from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from pepl_sales.pepl_sales.doctype.vendor_approval_status.vendor_approval_sync import (
    get_applicable_stages,
    normalize_stage_value,
    synchronize_requirement_rows,
)


TEST_REQUIREMENT_CODES = (
    "TEST-RW-APPLIED-SYNC",
    "TEST-RW-DEVELOPMENTAL-SYNC",
)


class TestVendorApprovalRequirementSync(FrappeTestCase):
    def setUp(self):
        super().setUp()

        self._ensure_requirement(
            requirement_code="TEST-RW-APPLIED-SYNC",
            requirement_name="Test Applied Requirement",
            approval_stage="Applied",
            mandatory=1,
            sequence=9901,
        )

        self._ensure_requirement(
            requirement_code="TEST-RW-DEVELOPMENTAL-SYNC",
            requirement_name="Test Developmental Requirement",
            approval_stage="Developmental",
            mandatory=0,
            sequence=9902,
        )

    def tearDown(self):
        for requirement_code in TEST_REQUIREMENT_CODES:
            if frappe.db.exists(
                "PEPL Vendor Approval Requirement",
                requirement_code,
            ):
                frappe.delete_doc(
                    "PEPL Vendor Approval Requirement",
                    requirement_code,
                    force=True,
                    ignore_permissions=True,
                )

        super().tearDown()

    def _ensure_requirement(
        self,
        *,
        requirement_code,
        requirement_name,
        approval_stage,
        mandatory,
        sequence,
    ):
        if frappe.db.exists(
            "PEPL Vendor Approval Requirement",
            requirement_code,
        ):
            return

        frappe.get_doc(
            {
                "doctype": "PEPL Vendor Approval Requirement",
                "requirement_code": requirement_code,
                "requirement_name": requirement_name,
                "sector": "Railways",
                "approval_stage": approval_stage,
                "document_category": "Manual Upload",
                "document_name": requirement_name,
                "mandatory": mandatory,
                "auto_fetch_source": "None",
                "item_specific": 0,
                "sales_order_specific": 0,
                "validity_required": 0,
                "sequence": sequence,
                "active": 1,
            }
        ).insert(ignore_permissions=True)

    def _new_approval(self, railway_stage):
        doc = frappe.new_doc("Vendor Approval Status")
        doc.sector = "Railways"
        doc.railways_stage = railway_stage
        return doc

    def _row_by_requirement(self, doc, requirement_code):
        for row in doc.vendor_approval_documents or []:
            if row.requirement_code == requirement_code:
                return row

        return None

    def test_stage_normalization(self):
        self.assertEqual(
            normalize_stage_value(
                "Railways",
                "Unapproved",
            ),
            "Applied",
        )

        self.assertEqual(
            normalize_stage_value(
                "Railways",
                "Developmental",
            ),
            "Developmental",
        )

        self.assertEqual(
            normalize_stage_value(
                "Railways",
                "Approved",
            ),
            "Approved",
        )

        self.assertEqual(
            normalize_stage_value(
                "Defence",
                "Source Development",
            ),
            "Developmental",
        )

        self.assertEqual(
            normalize_stage_value(
                "Defence",
                "Approved / Established",
            ),
            "Established",
        )

    def test_cumulative_stage_sequence(self):
        self.assertEqual(
            get_applicable_stages(
                "Railways",
                "Applied",
            ),
            ["Applied"],
        )

        self.assertEqual(
            get_applicable_stages(
                "Railways",
                "Developmental",
            ),
            [
                "Applied",
                "Developmental",
            ],
        )

        self.assertEqual(
            get_applicable_stages(
                "Railways",
                "Approved",
            ),
            [
                "Applied",
                "Developmental",
                "Approved",
            ],
        )

        self.assertEqual(
            get_applicable_stages(
                "Defence",
                "Established",
            ),
            [
                "Developmental",
                "Established",
            ],
        )

    def test_sync_is_cumulative_and_idempotent(self):
        doc = self._new_approval("Developmental")

        first_result = synchronize_requirement_rows(doc)

        applied_row = self._row_by_requirement(
            doc,
            "TEST-RW-APPLIED-SYNC",
        )
        developmental_row = self._row_by_requirement(
            doc,
            "TEST-RW-DEVELOPMENTAL-SYNC",
        )

        self.assertIsNotNone(applied_row)
        self.assertIsNotNone(developmental_row)

        self.assertEqual(
            doc.normalized_approval_stage,
            "Developmental",
        )

        self.assertEqual(
            applied_row.is_active_requirement,
            1,
        )
        self.assertEqual(
            developmental_row.is_active_requirement,
            1,
        )

        count_before_second_sync = len(
            doc.vendor_approval_documents or []
        )

        second_result = synchronize_requirement_rows(doc)

        count_after_second_sync = len(
            doc.vendor_approval_documents or []
        )

        self.assertEqual(
            count_before_second_sync,
            count_after_second_sync,
        )

        self.assertEqual(
            len(
                [
                    row
                    for row in doc.vendor_approval_documents
                    if (
                        row.requirement_code
                        == "TEST-RW-APPLIED-SYNC"
                    )
                ]
            ),
            1,
        )

        self.assertEqual(
            len(
                [
                    row
                    for row in doc.vendor_approval_documents
                    if (
                        row.requirement_code
                        == "TEST-RW-DEVELOPMENTAL-SYNC"
                    )
                ]
            ),
            1,
        )

        self.assertGreaterEqual(
            first_result["created"],
            2,
        )
        self.assertEqual(
            second_result["created"],
            0,
        )

    def test_backward_stage_marks_later_requirement_historical(self):
        doc = self._new_approval("Developmental")

        synchronize_requirement_rows(doc)

        developmental_row = self._row_by_requirement(
            doc,
            "TEST-RW-DEVELOPMENTAL-SYNC",
        )

        self.assertIsNotNone(developmental_row)
        self.assertEqual(
            developmental_row.is_active_requirement,
            1,
        )

        doc.railways_stage = "Unapproved"

        synchronize_requirement_rows(doc)

        applied_row = self._row_by_requirement(
            doc,
            "TEST-RW-APPLIED-SYNC",
        )
        developmental_row = self._row_by_requirement(
            doc,
            "TEST-RW-DEVELOPMENTAL-SYNC",
        )

        self.assertEqual(
            doc.normalized_approval_stage,
            "Applied",
        )

        self.assertEqual(
            applied_row.is_active_requirement,
            1,
        )
        self.assertEqual(
            applied_row.is_historical,
            0,
        )

        self.assertEqual(
            developmental_row.is_active_requirement,
            0,
        )
        self.assertEqual(
            developmental_row.is_historical,
            1,
        )
        self.assertEqual(
            developmental_row.requirement_status,
            "Superseded",
        )

    def test_manual_rows_are_preserved(self):
        doc = self._new_approval("Unapproved")

        manual_row = doc.append(
            "vendor_approval_documents",
            {},
        )
        manual_row.document_source = "Upload File"
        manual_row.document_type = "Other"
        manual_row.document_name = "Manual Historical Evidence"
        manual_row.file_attach = "/private/files/test-evidence.pdf"

        synchronize_requirement_rows(doc)

        preserved_rows = [
            row
            for row in doc.vendor_approval_documents
            if (
                row.document_name
                == "Manual Historical Evidence"
            )
        ]

        self.assertEqual(
            len(preserved_rows),
            1,
        )
        self.assertFalse(
            preserved_rows[0].requirement_code
        )
        self.assertEqual(
            preserved_rows[0].file_attach,
            "/private/files/test-evidence.pdf",
        )
