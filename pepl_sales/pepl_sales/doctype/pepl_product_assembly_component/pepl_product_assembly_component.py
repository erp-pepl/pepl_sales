import frappe
from frappe import _
from frappe.model.document import Document


class PEPLProductAssemblyComponent(Document):
    def validate(self):
        if self.component_type == "Sub-Assembly (PEPL Product)":
            if not self.component_product:
                frappe.throw(_("Sub-Assembly Product must be specified"))
            self.component_item = None
        elif self.component_type == "Simple Component (Item only)":
            if not self.component_item:
                frappe.throw(_("Component Item must be specified"))
            self.component_product = None
