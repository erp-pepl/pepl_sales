import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class VendorApprovalStatus(Document):
    def validate(self):
        # Sector-specific stage validation
        if self.sector == "Railways":
            if not self.railways_stage:
                frappe.throw(_("Railways Approval Stage is required when sector is Railways"))
            self.defence_stage = None
        elif self.sector == "Defence":
            if not self.defence_stage:
                frappe.throw(_("Defence Approval Stage is required when sector is Defence"))
            self.railways_stage = None

        # Approval reference recommended if approved
        if self.sector == "Railways" and self.railways_stage in ["Developmental", "Approved"]:
            if not self.approval_reference:
                frappe.msgprint(
                    _("Approval reference number recommended for {0} stage").format(self.railways_stage),
                    indicator="orange",
                    alert=True
                )

        if self.sector == "Defence" and self.defence_stage == "Approved / Established":
            if not self.approval_reference:
                frappe.msgprint(
                    _("Approval reference number recommended for Approved / Established stage"),
                    indicator="orange",
                    alert=True
                )

        # Warn if any document is expired
        if self.vendor_approval_documents:
            for doc in self.vendor_approval_documents:
                if doc.expiry_date and getdate(doc.expiry_date) < getdate(today()):
                    frappe.msgprint(
                        _("Document {0} expired on {1}").format(
                            doc.document_type, doc.expiry_date
                        ),
                        indicator="red",
                        alert=True
                    )


@frappe.whitelist()
def get_required_documents(sector, stage):
    """Returns required documents for vendor approval at given stage.

    Returns BOTH baseline (always-required) PEPL bid documents AND
    stage-specific docs. This ensures Auto-Generate Document Checklist
    always produces at least minimum standard docs.
    """

    # BASELINE — these docs are required for ANY tender, regardless of stage
    baseline_docs = [
        "GST Certificate",
        "Udyam Registration",
        "PAN Card",
        "MSME Certificate",
        "Bank Details (Cancelled Cheque or Letter)",
        "Authorisation Letter for Bid Submission",
        "Bid Securing Declaration (BSD)"
    ]

    # STAGE-SPECIFIC docs — added on top of baseline
    stage_docs_map = {
        # Railways stages
        "Unapproved": [
            "Capability Statement",
            "Plant and Machinery List",
            "Quality Control Process Document",
            "Past Experience / Similar Work Done"
        ],
        "Developmental": [
            "Centralised Vendor Registration Certificate",
            "Quality Assurance Plan (QAP)",
            "Inspection Plan",
            "Material Test Certificates (Sample)",
            "Technical Capability Document"
        ],
        "Approved": [
            "Quality Assurance Plan (QAP) for this Item",
            "Manufacturing Process Document",
            "Lot Inspection History",
            "Recent CCA / Final IC Records"
        ],
        # Defence stages
        "Source Development": [
            "Company Profile",
            "Plant and Machinery List",
            "Past Defence Experience (if any)",
            "Quality System Documentation",
            "ISO 9001 / AS9100 (if available)"
        ],
        "Established": [
            "DGQA / DQA Approval Certificate",
            "AS9100 Certificate",
            "Latest Audit Reports",
            "Source Inspection Plan"
        ]
    }

    # Get stage-specific docs
    stage_specific = stage_docs_map.get(stage, [])

    # Combine baseline + stage-specific (deduplicated, order preserved)
    all_docs = list(dict.fromkeys(baseline_docs + stage_specific))

    return all_docs


@frappe.whitelist()
def get_approval_status_for_item(item, sector):
    """Fetch the current approval status for an Item in given sector.
    Used by Tender Management when a new tender is created."""

    record = frappe.db.get_value(
        "Vendor Approval Status",
        {"item": item, "sector": sector},
        ["name", "railways_stage", "defence_stage", "approval_date", "approval_reference"],
        as_dict=True
    )

    if not record:
        return {
            "exists": False,
            "stage": None,
            "message": f"No approval record found for {item} in {sector} sector"
        }

    stage = record.railways_stage if sector == "Railways" else record.defence_stage

    return {
        "exists": True,
        "name": record.name,
        "stage": stage,
        "approval_date": record.approval_date,
        "approval_reference": record.approval_reference,
        "required_documents": get_required_documents(sector, stage)
    }