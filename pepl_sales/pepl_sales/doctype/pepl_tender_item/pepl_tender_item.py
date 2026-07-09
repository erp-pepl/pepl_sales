import frappe
from frappe import _
from frappe.model.document import Document


class PEPLTenderItem(Document):
    def validate(self):
        if self.quantity and self.estimated_unit_price:
            self.estimated_total_value = self.quantity * self.estimated_unit_price

        if self.quantity and self.our_bid_unit_price:
            self.our_bid_total_value = self.quantity * self.our_bid_unit_price
