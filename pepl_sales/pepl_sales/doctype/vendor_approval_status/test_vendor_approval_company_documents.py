from __future__ import annotations

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from pepl_sales.pepl_sales.doctype.vendor_approval_status import (
    vendor_approval_sync,
)


class TestVendorApprovalCompanyDocuments(FrappeTestCase):
    def _requirement(self, document_name):
        return frappe._dict(
            {
                "document_name": document_name,
                "document_category": "Company Document",
                "auto_fetch_source":
                    "PEPL Company Document",
            }
        )

    def _row(self):
        return frappe._dict(
            {
                "document_source": "Upload File",
                "document_type": None,
                "linked_company_document": None,
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

    def _candidate(self, *, expiry_date=None):
        return frappe._dict(
            {
                "name": "TEST-PAN-MASTER",
                "document_type": "PAN Card",
                "current_version_number": "TEST-1.0",
                "current_version_file":
                    "/private/files/test-pan.pdf",
                "current_issue_date": "2026-08-03",
                "current_expiry_date": expiry_date,
                "current_reference_no":
                    "TEST-PAN-001",
            }
        )

    def test_valid_company_document_is_populated(self):
        row = self._row()
        requirement = self._requirement("PAN")

        with patch.object(
            vendor_approval_sync,
            "_get_company_document_candidate",
            return_value=self._candidate(
                expiry_date="2027-08-31"
            ),
        ):
            result = (
                vendor_approval_sync
                ._apply_company_document_source(
                    row,
                    requirement,
                )
            )

        self.assertEqual(result, "available")
        self.assertEqual(
            row.document_source,
            "Company Library",
        )
        self.assertEqual(
            row.linked_company_document,
            "TEST-PAN-MASTER",
        )
        self.assertEqual(
            row.file_attach,
            "/private/files/test-pan.pdf",
        )
        self.assertEqual(
            row.source_record_doctype,
            "PEPL Company Document",
        )
        self.assertEqual(
            row.source_version,
            "TEST-1.0",
        )
        self.assertEqual(
            row.requirement_status,
            "Available",
        )

    def test_manual_upload_is_not_overwritten(self):
        row = self._row()
        row.file_attach = (
            "/private/files/manual-pan.pdf"
        )

        requirement = self._requirement("PAN")

        with patch.object(
            vendor_approval_sync,
            "_get_company_document_candidate",
            return_value=self._candidate(
                expiry_date="2027-08-31"
            ),
        ) as selector:
            result = (
                vendor_approval_sync
                ._apply_company_document_source(
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
            "/private/files/manual-pan.pdf",
        )
        self.assertIsNone(
            row.linked_company_document
        )
        selector.assert_not_called()

    def test_expired_company_document_is_marked_expired(self):
        row = self._row()
        requirement = self._requirement("PAN")

        with patch.object(
            vendor_approval_sync,
            "_get_company_document_candidate",
            return_value=self._candidate(
                expiry_date="2025-08-31"
            ),
        ):
            result = (
                vendor_approval_sync
                ._apply_company_document_source(
                    row,
                    requirement,
                )
            )

        self.assertEqual(result, "expired")
        self.assertEqual(
            row.requirement_status,
            "Expired",
        )
        self.assertEqual(
            row.linked_company_document,
            "TEST-PAN-MASTER",
        )

    def test_missing_source_remains_pending(self):
        row = self._row()
        requirement = self._requirement("PAN")

        with patch.object(
            vendor_approval_sync,
            "_get_company_document_candidate",
            return_value=None,
        ):
            result = (
                vendor_approval_sync
                ._apply_company_document_source(
                    row,
                    requirement,
                )
            )

        self.assertEqual(result, "pending")
        self.assertEqual(
            row.requirement_status,
            "Pending",
        )
        self.assertIsNone(
            row.linked_company_document
        )

    def test_unknown_requirement_is_ignored(self):
        row = self._row()
        requirement = self._requirement(
            "Approved Drawing"
        )

        result = (
            vendor_approval_sync
            ._apply_company_document_source(
                row,
                requirement,
            )
        )

        self.assertEqual(
            result,
            "not-applicable",
        )
        self.assertIsNone(
            row.linked_company_document
        )
