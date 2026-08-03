from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from pepl_sales.pepl_sales.doctype.vendor_approval_status import (
    vendor_approval_sync,
)


class TestVendorApprovalProductDocuments(
    FrappeTestCase
):
    def _approval(self):
        return frappe._dict(
            {
                "item": "TEST-FG-ITEM",
                "sector": "Railways",
            }
        )

    def _row(self):
        return frappe._dict(
            {
                "document_source": "Upload File",
                "document_type": None,
                "linked_company_document": None,
                "linked_drawing_revision": None,
                "linked_specification": None,
                "file_attach": None,
                "issue_date": None,
                "expiry_date": None,
                "reference_no": None,
                "source_record_doctype": None,
                "source_record_name": None,
                "source_version": None,
                "requirement_status": "Pending",
            }
        )

    def _requirement(
        self,
        document_name,
        source,
    ):
        return frappe._dict(
            {
                "document_name": document_name,
                "document_category":
                    "Product Document",
                "auto_fetch_source": source,
            }
        )

    def _product(self):
        drawing = frappe._dict(
            {
                "name": "DRAWING-ROW-001",
                "idx": 1,
                "revision": "R1",
                "issue_date": "2026-08-03",
                "is_current": 1,
                "customer_approved": 1,
                "drawing_file":
                    "/private/files/test-drawing.pdf",
            }
        )

        specification = frappe._dict(
            {
                "name": "SPEC-ROW-001",
                "idx": 1,
                "spec_type":
                    "Customer Specification",
                "spec_title":
                    "Approved Test Specification",
                "reference_no": "TEST-SPEC-001",
                "issue_date": "2026-08-03",
                "status": "Active",
                "spec_file":
                    "/private/files/test-spec.pdf",
            }
        )

        return frappe._dict(
            {
                "name": "TEST-PRODUCT",
                "drawing_number":
                    "TEST-DRAWING-001",
                "drawing_revisions": [drawing],
                "specifications": [specification],
            }
        )

    def test_drawing_is_populated(self):
        row = self._row()
        requirement = self._requirement(
            "Approved Drawing",
            "PEPL Product Drawing Revision",
        )

        with patch.object(
            vendor_approval_sync,
            "_get_active_product_master",
            return_value=self._product(),
        ):
            result = (
                vendor_approval_sync
                ._apply_product_document_source(
                    self._approval(),
                    row,
                    requirement,
                )
            )

        self.assertEqual(result, "available")
        self.assertEqual(
            row.document_source,
            "Item Drawing",
        )
        self.assertEqual(
            row.linked_drawing_revision,
            "R1",
        )
        self.assertEqual(
            row.file_attach,
            "/private/files/test-drawing.pdf",
        )
        self.assertEqual(
            row.source_record_doctype,
            "PEPL Product Drawing Revision",
        )
        self.assertEqual(
            row.source_record_name,
            "DRAWING-ROW-001",
        )
        self.assertEqual(
            row.requirement_status,
            "Available",
        )

    def test_specification_is_populated(self):
        row = self._row()
        requirement = self._requirement(
            "Approved Specification",
            "PEPL Product Specification",
        )

        with patch.object(
            vendor_approval_sync,
            "_get_active_product_master",
            return_value=self._product(),
        ):
            result = (
                vendor_approval_sync
                ._apply_product_document_source(
                    self._approval(),
                    row,
                    requirement,
                )
            )

        self.assertEqual(result, "available")
        self.assertEqual(
            row.document_source,
            "Item Specification",
        )
        self.assertEqual(
            row.linked_specification,
            "Approved Test Specification",
        )
        self.assertEqual(
            row.file_attach,
            "/private/files/test-spec.pdf",
        )
        self.assertEqual(
            row.source_record_doctype,
            "PEPL Product Specification",
        )
        self.assertEqual(
            row.source_record_name,
            "SPEC-ROW-001",
        )
        self.assertEqual(
            row.requirement_status,
            "Available",
        )

    def test_manual_upload_is_preserved(self):
        row = self._row()
        row.file_attach = (
            "/private/files/manual-drawing.pdf"
        )

        requirement = self._requirement(
            "Approved Drawing",
            "PEPL Product Drawing Revision",
        )

        with patch.object(
            vendor_approval_sync,
            "_get_active_product_master",
        ) as selector:
            result = (
                vendor_approval_sync
                ._apply_product_document_source(
                    self._approval(),
                    row,
                    requirement,
                )
            )

        self.assertEqual(
            result,
            "manual-preserved",
        )
        self.assertEqual(
            row.file_attach,
            "/private/files/manual-drawing.pdf",
        )
        selector.assert_not_called()

    def test_missing_product_remains_pending(self):
        row = self._row()
        requirement = self._requirement(
            "Approved Drawing",
            "PEPL Product Drawing Revision",
        )

        with patch.object(
            vendor_approval_sync,
            "_get_active_product_master",
            return_value=None,
        ):
            result = (
                vendor_approval_sync
                ._apply_product_document_source(
                    self._approval(),
                    row,
                    requirement,
                )
            )

        self.assertEqual(result, "pending")
        self.assertEqual(
            row.requirement_status,
            "Pending",
        )

    def test_unapproved_drawing_is_rejected(self):
        product = self._product()
        product.drawing_revisions[0].customer_approved = 0

        candidate = (
            vendor_approval_sync
            ._get_product_drawing_candidate(product)
        )

        self.assertIsNone(candidate)

    def test_inactive_specification_is_rejected(self):
        product = self._product()
        product.specifications[0].status = "Draft"

        candidate = (
            vendor_approval_sync
            ._get_product_specification_candidate(
                product,
                "Railways",
            )
        )

        self.assertIsNone(candidate)
