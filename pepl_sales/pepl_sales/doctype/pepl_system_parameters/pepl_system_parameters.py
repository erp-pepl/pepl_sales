# Copyright (c) 2026, Parasramka Engineering Pvt. Ltd. and contributors
import frappe
from frappe.model.document import Document


class PEPLSystemParameters(Document):
    pass


def get_param(field_name, default=None):
    """Helper for other modules to safely read parameters."""
    try:
        return frappe.db.get_single_value("PEPL System Parameters", field_name) or default
    except Exception:
        return default
