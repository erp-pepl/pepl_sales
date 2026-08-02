from __future__ import annotations

import frappe

ROLES = (
    "PEPL Tender Viewer",
    "PEPL Tender Executive",
    "PEPL Tender Manager",
)

DOCUMENT_REQUIREMENTS = (
    ("PSD_BG_TEXT", "Bank Guarantee Text / Annexure", "Common", "PSD/BG Initiation", "PSD Tracker", "PSD/BG", 1, 0, 0, 10),
    ("PSD_BG_APPLICATION", "Bank Guarantee Application Form", "Common", "PSD/BG Initiation", "PSD Tracker", "PSD/BG", 1, 0, 0, 20),
    ("PSD_BG_DEBIT_AUTHORITY", "BG Request-cum-Debit Authority Letter", "Common", "PSD/BG Initiation", "PSD Tracker", "PSD/BG", 1, 0, 0, 30),
    ("PSD_BG_COLLECTION_AUTHORITY", "Authority Letter for Collection of BG", "Common", "BG Issuance and Submission", "PSD Tracker", "PSD/BG", 1, 0, 0, 40),
    ("PSD_FINAL_BG", "Final Bank Guarantee", "Common", "BG Issuance and Submission", "PSD Tracker", "PSD/BG", 0, 1, 1, 50),
    ("PSD_BG_SUBMISSION_COVER", "BG Submission Covering Letter", "Common", "BG Issuance and Submission", "PSD Tracker", "PSD/BG", 1, 0, 0, 60),
    ("PSD_RETURN_REQUEST", "PSD / Security Deposit Return Request", "Common", "PSD Return and Closure", "PSD Tracker", "PSD/BG", 1, 0, 0, 70),
    ("DRAWING_SPEC_REQUEST", "Drawing and Specification Request", "Common", "Engineering Documents", "Sales Order", "Engineering", 1, 0, 0, 100),
    ("APPROVED_DRAWING", "Approved Drawing", "Common", "Engineering Documents", "Sales Order", "Engineering", 0, 1, 1, 110),
    ("APPROVED_SPECIFICATION", "Approved Specification", "Common", "Engineering Documents", "Sales Order", "Engineering", 0, 1, 1, 120),
    ("PROOF_SCHEDULE_REQUEST", "Proof Schedule Request", "Common", "Engineering Documents", "Sales Order", "Engineering", 1, 0, 0, 130),
    ("RAW_MATERIAL_OFFER", "Raw Material Offer", "Common", "Raw Material Inspection", "Sales Order", "Inspection", 1, 0, 0, 200),
    ("QUALITY_SELF_CERTIFICATE", "Quality Self-Certificate", "Common", "Raw Material Inspection", "Sales Order", "Inspection", 1, 0, 0, 210),
    ("NABL_TEST_OFFER", "Material Offer to NABL Test Laboratory", "Common", "NABL Testing", "Sales Order", "Inspection", 1, 0, 0, 220),
    ("NABL_TEST_REPORT", "NABL Test Report", "Common", "NABL Testing", "Sales Order", "Inspection", 0, 1, 1, 230),
    ("LOT_NUMBER_REQUEST", "Lot Number and Lot Size Request", "Common", "Lot Formation", "Sales Order", "Inspection", 1, 0, 0, 240),
    ("BULK_LOT_OFFER", "Bulk Lot Offer to Consignee", "Common", "Bulk Inspection", "Sales Order", "Inspection", 1, 0, 0, 250),
    ("INSPECTION_CERTIFICATE", "Inspection Certificate / Inspection Note", "Railways", "Pre-Dispatch", "Sales Order", "Inspection", 0, 1, 1, 300),
    ("WORK_TEST_CERTIFICATE", "Work Test Certificate", "Common", "Pre-Dispatch", "Sales Order", "Dispatch", 1, 0, 0, 310),
    ("GST_CERTIFICATE", "GST Certificate", "Common", "Sales Invoice", "Sales Invoice", "Invoice", 1, 0, 0, 400),
    ("GST_SUMMARY", "GST Summary", "Common", "Sales Invoice", "Sales Invoice", "Invoice", 1, 0, 0, 410),
    ("GUARANTEE_CERTIFICATE", "After-Invoice Guarantee Certificate", "Common", "Sales Invoice", "Sales Invoice", "Invoice", 1, 0, 0, 420),
    ("DISPATCH_LABEL", "Dispatch Label / Sticker", "Common", "Dispatch", "Sales Order", "Dispatch", 1, 0, 0, 430),
    ("MATERIAL_RECEIPT", "Material Receipt / Customer Acknowledgement", "Common", "Dispatch", "Sales Order", "Dispatch", 0, 1, 1, 440),
    ("R_NOTE", "R-Note", "Railways", "Bill Submission/JCC", "Sales Invoice", "Invoice", 0, 1, 1, 500),
    ("JCC", "Joint Completion Certificate (JCC)", "Common", "Bill Submission/JCC", "Sales Invoice", "Invoice", 0, 1, 1, 510),
    ("CONTRACTOR_BILL", "Contractor's Bill", "Common", "Bill Submission/JCC", "Sales Invoice", "Invoice", 1, 0, 0, 520),
    ("BANK_MANDATE", "Bank Mandate", "Common", "Bill Submission/JCC", "Sales Invoice", "Invoice", 0, 1, 1, 530),
    ("PAYMENT_REQUEST", "Payment Request Letter", "Common", "Payment Follow-up", "Payment Tracker", "Payment", 1, 0, 0, 600),
)

VENDOR_REQUIREMENTS = (
    ("RW_APPLIED_PAN", "Railways Applied - PAN", "Railways", "Applied", "Company Document", "PAN", 1, "PEPL Company Document", 10),
    ("RW_APPLIED_UDYAM", "Railways Applied - Udyam Registration", "Railways", "Applied", "Company Document", "Udyam Registration", 1, "PEPL Company Document", 20),
    ("DEF_DEV_PAN", "Defence Developmental - PAN", "Defence", "Developmental", "Company Document", "PAN", 1, "PEPL Company Document", 10),
    ("DEF_DEV_UDYAM", "Defence Developmental - Udyam Registration", "Defence", "Developmental", "Company Document", "Udyam Registration", 1, "PEPL Company Document", 20),
    ("RW_DEV_APPROVED_DRAWING", "Railways Developmental - Approved Drawing", "Railways", "Developmental", "Product Document", "Approved Drawing", 0, "PEPL Product Drawing Revision", 100),
    ("RW_DEV_APPROVED_SPEC", "Railways Developmental - Approved Specification", "Railways", "Developmental", "Product Document", "Approved Specification", 0, "PEPL Product Specification", 110),
    ("DEF_DEV_APPROVED_DRAWING", "Defence Developmental - Approved Drawing", "Defence", "Developmental", "Product Document", "Approved Drawing", 0, "PEPL Product Drawing Revision", 100),
    ("DEF_DEV_APPROVED_SPEC", "Defence Developmental - Approved Specification", "Defence", "Developmental", "Product Document", "Approved Specification", 0, "PEPL Product Specification", 110),
)


def ensure_roles():
    for role_name in ROLES:
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(ignore_permissions=True)


def seed_document_requirements():
    for code, name, sector, stage, source, category, generated, external, evidence, sequence in DOCUMENT_REQUIREMENTS:
        if frappe.db.exists("PEPL Document Requirement", code):
            continue
        frappe.get_doc({
            "doctype": "PEPL Document Requirement",
            "document_code": code,
            "document_name": name,
            "sector": sector,
            "business_stage": stage,
            "source_transaction": source,
            "document_category": category,
            "generated_by_pepl": generated,
            "external_issued": external,
            "evidence_required": evidence,
            "mandatory": 0,
            "blocking_event": "None",
            "allow_multiple": int(code in {"APPROVED_DRAWING", "APPROVED_SPECIFICATION", "RAW_MATERIAL_OFFER", "NABL_TEST_REPORT", "BULK_LOT_OFFER", "MATERIAL_RECEIPT", "R_NOTE", "JCC", "CONTRACTOR_BILL", "PAYMENT_REQUEST"}),
            "sequence": sequence,
            "active": 1,
            "notes": "Seeded from the 24 July 2026 MoM and client reference pack. Non-blocking until UAT approval.",
        }).insert(ignore_permissions=True)


def seed_vendor_requirements():
    for code, name, sector, stage, category, document_name, mandatory, source, sequence in VENDOR_REQUIREMENTS:
        if frappe.db.exists("PEPL Vendor Approval Requirement", code):
            continue
        frappe.get_doc({
            "doctype": "PEPL Vendor Approval Requirement",
            "requirement_code": code,
            "requirement_name": name,
            "sector": sector,
            "approval_stage": stage,
            "document_category": category,
            "document_name": document_name,
            "mandatory": mandatory,
            "auto_fetch_source": source,
            "item_specific": int("Drawing" in document_name or "Specification" in document_name),
            "sequence": sequence,
            "active": 1,
            "notes": "Seeded from the MoM. Optional rows remain non-mandatory pending PEPL stage-matrix sign-off.",
        }).insert(ignore_permissions=True)


def ensure_foundation(reset_permissions=False):
    ensure_roles()
    if reset_permissions:
        for doctype in (
            "PEPL Tender",
            "PEPL Vendor Approval Requirement",
            "PEPL Document Requirement",
            "PEPL Standard Document Template",
            "PEPL Generated Document",
            "PEPL Vendor Product Supply History",
        ):
            if frappe.db.exists("DocType", doctype):
                frappe.permissions.reset_perms(doctype)
    if frappe.db.exists("DocType", "PEPL Document Requirement"):
        seed_document_requirements()
    if frappe.db.exists("DocType", "PEPL Vendor Approval Requirement"):
        seed_vendor_requirements()
    frappe.clear_cache()


def before_migrate():
    ensure_roles()


def after_migrate():
    ensure_foundation(reset_permissions=False)
