import frappe


PEPL_SALES_BUILD = "2026-07-14-document-checklist-v1"


@frappe.whitelist()
def get_build_info():
    return {
        "app": "pepl_sales",
        "build": PEPL_SALES_BUILD,
        "document_checklist_version": 1,
        "expected_defence_documents": [
            "Customer PO",
            "Material Receipt",
            "I-Note",
            "JCC",
        ],
    }


@frappe.whitelist()
def run_payment_tracker_ageing_diagnostic():
    """Run the normal payment-ageing job for controlled UAT."""
    frappe.only_for("System Manager")

    from pepl_sales.pepl_sales.api.payment_tracker_jobs import (
        update_all_payment_trackers_daily,
    )

    return update_all_payment_trackers_daily()
