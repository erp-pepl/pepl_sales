import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PEPLTenderPOSchedule(Document):
    def validate(self):
        if self.po_quantity and self.po_rate:
            self.po_total = flt(self.po_quantity) * flt(self.po_rate)
