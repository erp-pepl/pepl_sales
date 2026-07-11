import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import date_diff, getdate, today


EXPIRY_WARNING_DAYS = 30


class VendorApprovalStatus(Document):
    def autoname(self):
        # Sequential naming allows multiple historical records while duplicate
        # checking remains a warning rather than a hard block.
        self.name = make_autoname("VAS-.YYYY.-.#####")

    def validate(self):
        self._normalise_stage()
        self._calculate_approval_health()
        self._warn_if_duplicate()
        self._warn_if_reference_missing()
        self._warn_if_documents_expired()

    def _normalise_stage(self):
        """Apply safe baseline stages without blocking the user."""

        if self.sector == "Railways":
            self.defence_stage = None

            if not self.railways_stage:
                self.railways_stage = "Unapproved"
                frappe.msgprint(
                    _(
                        "Railways Approval Stage was blank and has been set "
                        "to Unapproved."
                    ),
                    indicator="orange",
                    alert=True,
                )

        elif self.sector == "Defence":
            self.railways_stage = None

            if not self.defence_stage:
                self.defence_stage = "Source Development"
                frappe.msgprint(
                    _(
                        "Defence Approval Stage was blank and has been set "
                        "to Source Development."
                    ),
                    indicator="orange",
                    alert=True,
                )

    def _get_stage(self):
        if self.sector == "Railways":
            return self.railways_stage

        if self.sector == "Defence":
            return self.defence_stage

        return None

    def _calculate_approval_health(self):
        """
        Effective expiry is the earliest of:
        - Next review / renewal date
        - Any attached approval document expiry
        """

        expiry_dates = []

        if self.next_review_date:
            expiry_dates.append(getdate(self.next_review_date))

        for row in self.vendor_approval_documents or []:
            if row.expiry_date:
                expiry_dates.append(getdate(row.expiry_date))

        if not expiry_dates:
            self.effective_expiry_date = None
            self.days_to_expiry = 0
            self.approval_health = "No Expiry Set"
            self.approval_warning = (
                "No approval review or document expiry date has been set."
            )
            return

        effective_expiry = min(expiry_dates)
        days_remaining = date_diff(effective_expiry, getdate(today()))

        self.effective_expiry_date = effective_expiry
        self.days_to_expiry = days_remaining

        if days_remaining < 0:
            self.approval_health = "Expired"
            self.approval_warning = (
                f"Approval expired on {effective_expiry}."
            )

        elif days_remaining <= EXPIRY_WARNING_DAYS:
            self.approval_health = "Expiring Soon"
            self.approval_warning = (
                f"Approval expires in {days_remaining} day(s) "
                f"on {effective_expiry}."
            )

        else:
            self.approval_health = "Active"
            self.approval_warning = ""

    def _warn_if_duplicate(self):
        """
        Warn about another record for the same Customer + Item + Sector.

        We deliberately do not block saving because PEPL follows the
        warn-and-override operating principle and may retain historical records.
        """

        if not self.customer or not self.item or not self.sector:
            return

        filters = {
            "customer": self.customer,
            "item": self.item,
            "sector": self.sector,
            "name": ["!=", self.name or ""],
        }

        duplicates = frappe.get_all(
            "Vendor Approval Status",
            filters=filters,
            fields=[
                "name",
                "railways_stage",
                "defence_stage",
                "modified",
            ],
            order_by="modified desc",
            limit=5,
        )

        if not duplicates:
            return

        existing_names = ", ".join(d.name for d in duplicates)

        warning = (
            "Another Vendor Approval Status record exists for this "
            f"Customer + Item + Sector: {existing_names}. "
            "Please verify which record is current."
        )

        self.approval_warning = (
            f"{self.approval_warning}\n{warning}".strip()
        )

        frappe.msgprint(
            _(warning),
            title=_("Possible Duplicate Approval Record"),
            indicator="orange",
        )

    def _warn_if_reference_missing(self):
        stage = self._get_stage()

        approved_stages = {
            "Developmental",
            "Approved",
            "Approved / Established",
        }

        if stage in approved_stages and not self.approval_reference:
            frappe.msgprint(
                _(
                    "Approval reference number is recommended for "
                    "stage {0}."
                ).format(stage),
                indicator="orange",
                alert=True,
            )

    def _warn_if_documents_expired(self):
        for row in self.vendor_approval_documents or []:
            if (
                row.expiry_date
                and getdate(row.expiry_date) < getdate(today())
            ):
                frappe.msgprint(
                    _("Document {0} expired on {1}.").format(
                        row.document_type or row.document_name,
                        row.expiry_date,
                    ),
                    indicator="red",
                    alert=True,
                )


def _normalise_stage(stage):
    aliases = {
        "Established": "Approved / Established",
    }
    return aliases.get(stage, stage)


@frappe.whitelist()
def get_required_documents(sector, stage):
    """
    Return baseline plus sector/stage-specific bid documents.
    """

    stage = _normalise_stage(stage)

    baseline_docs = [
        "GST Certificate",
        "Udyam Registration",
        "PAN Card",
        "MSME Certificate",
        "Bank Details (Cancelled Cheque or Letter)",
        "Authorisation Letter for Bid Submission",
        "Bid Securing Declaration (BSD)",
    ]

    stage_docs_map = {
        "Unapproved": [
            "Capability Statement",
            "Plant and Machinery List",
            "Quality Control Process Document",
            "Past Experience / Similar Work Done",
        ],
        "Developmental": [
            "Centralised Vendor Registration Certificate",
            "Quality Assurance Plan (QAP)",
            "Inspection Plan",
            "Material Test Certificates (Sample)",
            "Technical Capability Document",
        ],
        "Approved": [
            "Quality Assurance Plan (QAP) for this Item",
            "Manufacturing Process Document",
            "Lot Inspection History",
            "Recent CCA / Final IC Records",
        ],
        "Source Development": [
            "Company Profile",
            "Plant and Machinery List",
            "Past Defence Experience (if any)",
            "Quality System Documentation",
            "ISO 9001 / AS9100 (if available)",
        ],
        "Approved / Established": [
            "DGQA / DQA Approval Certificate",
            "AS9100 Certificate",
            "Latest Audit Reports",
            "Source Inspection Plan",
        ],
    }

    stage_specific = stage_docs_map.get(stage, [])

    return list(dict.fromkeys(baseline_docs + stage_specific))


@frappe.whitelist()
def get_approval_status_for_item(customer, item, sector):
    """
    Return the most recently modified approval for a specific
    Customer + Item + Sector combination.
    """

    if not customer or not item or not sector:
        return {
            "exists": False,
            "stage": None,
            "health": "Missing",
            "warning": (
                "Customer, Item and Sector are required to check approval."
            ),
            "required_documents": get_required_documents(
                sector or "Railways",
                "Unapproved",
            ),
        }

    records = frappe.get_all(
        "Vendor Approval Status",
        filters={
            "customer": customer,
            "item": item,
            "sector": sector,
        },
        fields=[
            "name",
            "railways_stage",
            "defence_stage",
            "approval_date",
            "approval_reference",
            "approval_health",
            "effective_expiry_date",
            "days_to_expiry",
            "approval_warning",
            "modified",
        ],
        order_by="modified desc",
        limit=10,
    )

    if not records:
        fallback_stage = (
            "Unapproved"
            if sector == "Railways"
            else "Source Development"
        )

        return {
            "exists": False,
            "name": None,
            "stage": "No Record",
            "health": "Missing",
            "expiry_date": None,
            "warning": (
                f"No approval record found for Customer {customer}, "
                f"Item {item}, Sector {sector}."
            ),
            "required_documents": get_required_documents(
                sector,
                fallback_stage,
            ),
        }

    record = records[0]

    stage = (
        record.railways_stage
        if sector == "Railways"
        else record.defence_stage
    )

    duplicate_warning = ""

    if len(records) > 1:
        duplicate_warning = (
            f"{len(records)} approval records exist for this "
            "Customer + Item + Sector. "
            f"Using the most recently modified record {record.name}."
        )

    warning = "\n".join(
        filter(
            None,
            [
                record.approval_warning,
                duplicate_warning,
            ],
        )
    )

    return {
        "exists": True,
        "name": record.name,
        "stage": stage,
        "health": record.approval_health or "No Expiry Set",
        "expiry_date": record.effective_expiry_date,
        "days_to_expiry": record.days_to_expiry,
        "approval_date": record.approval_date,
        "approval_reference": record.approval_reference,
        "warning": warning,
        "required_documents": get_required_documents(sector, stage),
    }
