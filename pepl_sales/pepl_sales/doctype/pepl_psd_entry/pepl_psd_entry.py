import frappe
from frappe.model.document import Document


class PEPLPSDEntry(Document):
    """PSD Entry — child of PEPL PSD Tracker.
    Calculation logic lives in parent (PEPL PSD Tracker.validate())
    because Frappe doesn't run child validate() when parent is saved."""
    pass
