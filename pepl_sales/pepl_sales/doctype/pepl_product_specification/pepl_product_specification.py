import frappe
from frappe import _
from frappe.model.document import Document


class PEPLProductSpecification(Document):
    def validate(self):
        if self.status != "Draft" and not self.spec_file and not self.spec_text:
            frappe.msgprint(
                _("Specification {0} has neither a file nor text content. Add one before activating.").format(
                    self.spec_title
                ),
                indicator="orange",
                alert=True,
            )
