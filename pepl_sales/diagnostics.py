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
