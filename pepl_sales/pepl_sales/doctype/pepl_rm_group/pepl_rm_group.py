import frappe
from frappe.model.document import Document


class PEPLRMGroup(Document):
    def before_save(self):
        if self.auto_sync_to_item_group:
            self._create_item_group()

    def _create_item_group(self):
        """Auto-sync Link Item Group under parent driven by parent_category."""
        if not self.auto_sync_to_item_group:
            return

        PARENT_MAP = {
            "Raw Material": "Raw Material",
            "Administrative Purchases": "Administrative Purchases",
            "Process Services": "Process Services",
            "Standalone": "All Item Groups",
        }
        cat = getattr(self, "parent_category", None) or "Raw Material"
        parent = PARENT_MAP.get(cat, "Raw Material")

        if not frappe.db.exists("Item Group", parent):
            frappe.log_error(
                "Parent Item Group '{}' missing for RM Group '{}'".format(parent, self.name),
                "PEPL RM Group sync",
            )
            return

        ig_name = self.group_name
        if frappe.db.exists("Item Group", ig_name):
            self.linked_item_group = ig_name
            return

        try:
            ig = frappe.new_doc("Item Group")
            ig.item_group_name = ig_name
            ig.parent_item_group = parent
            ig.is_group = 0
            ig.insert(ignore_permissions=True)
            self.linked_item_group = ig.name
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"PEPL RM Group Item Group create failed: {self.name}",
            )
