import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today, date_diff


class PEPLPaymentTracker(Document):
    def validate(self):
        if not self.tracker_id:
            self.tracker_id = self.name

        if self.linked_sales_invoice and not self.sector:
            self._fetch_sector_from_invoice()

        if self.linked_sales_invoice and not self.linked_sales_order:
            self._fetch_so_from_invoice()

        self.calculate_payment_summary()

        # Amount Reconciled = min(Net Receivable, Gross Payment Realised)
        self.amount_reconciled = min(
            flt(self.net_amount_receivable),
            flt(self.gross_payment_realised)
        )

        # Days Outstanding + Ageing Bucket (MSME 45-day rule)
        if (
            self.invoice_date
            and flt(self.total_outstanding) > 0
            and self.payment_status not in {"Reconciled", "Closed"}
        ):
            self.days_outstanding = max(
                date_diff(today(), self.invoice_date),
                0,
            )

            if self.days_outstanding <= 30:
                self.ageing_bucket = "0-30 days"
            elif self.days_outstanding <= 45:
                self.ageing_bucket = "31-45 days"
            else:
                self.ageing_bucket = "45+ days (MSME breach)"
        else:
            self.days_outstanding = 0
            self.ageing_bucket = "0-30 days"

        self.last_update_date = today()
        self._auto_advance_status()

    def calculate_payment_summary(self):
        """
        Calculate payment receipts, deductions, recoverable amounts,
        written-off amounts and the remaining invoice outstanding.
        """

        total_bank_credit = sum(
            flt(receipt.amount_received)
            for receipt in self.payment_receipts or []
        )

        tds = flt(self.tds_deducted)
        sd = flt(self.sd_deducted)
        ld = flt(self.ld_deducted)
        other = flt(self.other_deductions)
        invoice_amount = flt(self.invoice_amount)

        self.total_amount_received = total_bank_credit
        self.gross_payment_realised = (
            total_bank_credit
            + tds
            + sd
            + ld
            + other
        )
        self.total_recoverable_held = tds + sd
        self.total_written_off = ld + other

        self.total_outstanding = max(
            invoice_amount - flt(self.gross_payment_realised),
            0,
        )

        if not flt(self.net_amount_receivable):
            self.net_amount_receivable = invoice_amount


    def _fetch_sector_from_invoice(self):
        customer = frappe.db.get_value(
            "Sales Invoice", self.linked_sales_invoice, "customer"
        )
        if not customer:
            return
        cg = frappe.db.get_value("Customer", customer, "customer_group")
        if not cg:
            return
        if "Railway" in cg:
            self.sector = "Railways"
        elif "Defence" in cg:
            self.sector = "Defence"
        elif "Private" in cg:
            self.sector = "Private"
        else:
            self.sector = "Others"

    def _fetch_so_from_invoice(self):
        try:
            invoice = frappe.get_doc("Sales Invoice", self.linked_sales_invoice)
            if invoice.items:
                first_so = invoice.items[0].sales_order
                if first_so:
                    self.linked_sales_order = first_so
        except Exception:
            pass

    def _auto_advance_status(self):
        """Smart status progression based on filled fields."""
        if self.payment_status in ["Closed", "Reconciled"]:
            return

        # Fully realised against invoice (gross = bank + deductions)
        if (flt(self.gross_payment_realised) >= flt(self.net_amount_receivable)
                and flt(self.net_amount_receivable) > 0):
            self.payment_status = "Reconciled"
            return

        # Any payment received
        if flt(self.total_amount_received) > 0:
            if self.payment_status not in ["Payment Received", "Reconciled", "Closed"]:
                self.payment_status = "Payment Received"
                return

        if self.sector == "Railways":
            if self.co7_number and self.payment_status in [
                "Pending Dispatch", "Dispatched", "R-Note Received", "Bills Submitted"
            ]:
                self.payment_status = "CO7 Issued"
            elif self.bills_submission_date and self.payment_status in [
                "Pending Dispatch", "Dispatched", "R-Note Received"
            ]:
                self.payment_status = "Bills Submitted"
            elif self.rnote_number and self.payment_status in ["Pending Dispatch", "Dispatched"]:
                self.payment_status = "R-Note Received"

        elif self.sector == "Defence":
            if self.jcc_number and self.payment_status in [
                "Pending Dispatch", "Dispatched", "I-Note Received"
            ]:
                self.payment_status = "JCC Issued"
            elif self.inote_number and self.payment_status in ["Pending Dispatch", "Dispatched"]:
                self.payment_status = "I-Note Received"
            elif self.bills_submission_date and self.payment_status in [
                "Pending Dispatch", "Dispatched", "I-Note Received", "JCC Issued"
            ]:
                self.payment_status = "Bills Submitted"

        elif self.sector == "Private":
            if self.bills_submission_date and self.payment_status == "Dispatched":
                self.payment_status = "Bills Submitted"

        if self.dispatch_date and self.payment_status == "Pending Dispatch":
            self.payment_status = "Dispatched"


@frappe.whitelist()
def create_payment_tracker_for_invoice(sales_invoice_name):
    """Auto-create Payment Tracker when Sales Invoice is submitted.
    Idempotent — returns existing tracker if already created.
    """
    existing = frappe.db.exists(
        "PEPL Payment Tracker",
        {"linked_sales_invoice": sales_invoice_name}
    )
    if existing:
        return {"created": False, "tracker_name": existing}

    invoice = frappe.get_doc("Sales Invoice", sales_invoice_name)

    sector = "Others"
    if invoice.customer:
        cg = frappe.db.get_value("Customer", invoice.customer, "customer_group")
        if cg:
            if "Railway" in cg:
                sector = "Railways"
            elif "Defence" in cg:
                sector = "Defence"
            elif "Private" in cg:
                sector = "Private"

    linked_so = None
    if invoice.items:
        linked_so = invoice.items[0].sales_order

    tracker = frappe.new_doc("PEPL Payment Tracker")
    tracker.linked_sales_invoice = invoice.name
    tracker.linked_sales_order = linked_so
    tracker.customer = invoice.customer
    tracker.sector = sector
    tracker.invoice_date = invoice.posting_date
    tracker.invoice_amount = invoice.grand_total
    tracker.payment_status = "Pending Dispatch"
    tracker.insert(ignore_permissions=True)

    return {
        "created": True,
        "tracker_name": tracker.name,
        "sector": sector,
        "invoice_amount": invoice.grand_total,
        "linked_so": linked_so
    }
