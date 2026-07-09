from frappe.model.document import Document
from frappe.utils import flt


class PEPLCSTComponent(Document):
    def validate(self):
        self._apply_input_rate_to_cost()

        if self.manufactured_or_bought_out == "Manufactured":
            self.component_subtotal = (
                flt(self.raw_material_cost)
                + flt(self.machining_cost)
                + flt(self.surface_treatment_cost)
                + flt(self.component_other_charges)
            )
            self.bought_out_cost = 0
        elif self.manufactured_or_bought_out == "Bought Out":
            self.component_subtotal = (
                flt(self.bought_out_cost)
                + flt(self.surface_treatment_cost)
                + flt(self.component_other_charges)
            )
            self.raw_material_cost = 0
            self.machining_cost = 0

    def _apply_input_rate_to_cost(self):
        """If input_rate_per_unit is set, auto-calculate the appropriate
        cost field as rate × quantity_per_assembly."""

        if not getattr(self, "input_rate_per_unit", None):
            return

        rate = flt(self.input_rate_per_unit)
        qty = flt(self.quantity_per_assembly) or 1.0
        amount = rate * qty

        is_bought_out = (self.manufactured_or_bought_out or "").strip() == "Bought Out"
        target_field = "bought_out_cost" if is_bought_out else "raw_material_cost"

        setattr(self, target_field, amount)
        self.rate_source = (
            f"From Per-Unit Rate: ₹{rate:.2f} × {qty:g} = ₹{amount:.2f}"
        )
