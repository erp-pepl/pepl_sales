import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class PEPLVendorProductSupplyHistory(Document):
    def validate(self):
        if self.invoice_date and self.dispatch_date and getdate(self.dispatch_date) < getdate(self.invoice_date):
            frappe.throw(_("Dispatch Date cannot be earlier than Invoice Date."))
        if self.sales_invoice:
            row = frappe.db.get_value("Sales Invoice", self.sales_invoice, ["customer", "posting_date"], as_dict=True)
            if row:
                self.customer = self.customer or row.customer
                self.invoice_date = self.invoice_date or row.posting_date
