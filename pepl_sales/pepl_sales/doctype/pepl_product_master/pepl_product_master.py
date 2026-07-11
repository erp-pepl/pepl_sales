import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class PEPLProductMaster(Document):
    def autoname(self):
        from frappe.model.naming import make_autoname
        self.product_code = make_autoname("PRD-.####")
        self.name = self.product_code

    def before_save(self):
        # Auto-fill HSN/SAC default for Railway sector if blank
        if not self.hsn_sac_code and self.sector == "Railways":
            self.hsn_sac_code = "86072900"

        # Auto-create or fetch linked Item
        if not self.linked_item:
            self._create_linked_item()

        # Auto-fetch BOM if linked Item has one
        if self.linked_item and not self.linked_bom:
            bom = frappe.db.get_value(
                "BOM",
                {"item": self.linked_item, "is_active": 1, "is_default": 1},
                "name"
            )
            if bom:
                self.linked_bom = bom

    def validate(self):
        # Validate drawing revisions
        if self.drawing_revisions:
            current_revs = [r for r in self.drawing_revisions if r.is_current]

            if len(current_revs) == 0 and self.drawing_revisions:
                sorted_revs = sorted(
                    self.drawing_revisions,
                    key=lambda r: getdate(r.issue_date) if r.issue_date else getdate("1900-01-01"),
                    reverse=True
                )
                sorted_revs[0].is_current = 1
                current_revs = [sorted_revs[0]]
                frappe.msgprint(
                    _("Auto-marked latest revision as current"),
                    indicator="blue",
                    alert=True
                )

            if len(current_revs) > 1:
                frappe.throw(_("Only one drawing revision can be 'Current'"))

            if current_revs:
                current = current_revs[0]
                self.current_drawing_revision = current.revision
                self.current_drawing_file = current.drawing_file

        # Validate product type vs assembly components
        if self.product_type == "Single Component" and self.assembly_components:
            frappe.throw(_("Single Component products cannot have Assembly Components."))

    def _create_linked_item(self):
        """Auto-create an ERPNext Item if not linked."""
        existing = frappe.db.get_value(
            "Item",
            {"item_name": self.product_name},
            "name"
        )
        if existing:
            self.linked_item = existing
            return

        # Determine item group based on sector
        item_group = "Finished Goods"
        if self.sector == "Railways":
            item_group = "Railway Components"
        elif self.sector == "Defence":
            item_group = "Defence Components"
        elif self.sector == "Private":
            item_group = "Private Sector Components"

        if not frappe.db.exists("Item Group", item_group):
            item_group = "Finished Goods"
        if not frappe.db.exists("Item Group", item_group):
            item_group = "All Item Groups"

        item_code = self.product_code or self.product_name

        try:
            item = frappe.new_doc("Item")
            item.item_code = item_code
            item.item_name = self.product_name
            item.item_group = item_group
            item.stock_uom = "Nos"
            item.is_stock_item = 1
            item.include_item_in_manufacturing = 1

            # Pass HSN/SAC code to avoid Item creation error
            if self.hsn_sac_code:
                item.gst_hsn_code = self.hsn_sac_code
            elif self.sector == "Railways":
                item.gst_hsn_code = "86072900"

            # Pass custom fields if they exist on Item DocType
            if self.drawing_number and frappe.db.has_column("Item", "custom_drawing_no"):
                item.custom_drawing_no = self.drawing_number

            if self.pl_number and frappe.db.has_column("Item", "custom_pl_no"):
                item.custom_pl_no = self.pl_number

            if self.sector and frappe.db.has_column("Item", "custom_sector"):
                item.custom_sector = self.sector

            item.insert(ignore_permissions=True)
            self.linked_item = item.name

            frappe.msgprint(
                _("Auto-created ERPNext Item: {0} (HSN: {1})").format(
                    item.name, item.gst_hsn_code or "Not Set"
                ),
                indicator="green",
                alert=True
            )
        except Exception as e:
            frappe.throw(
                _("Failed to auto-create Item: {0}. Please ensure HSN/SAC Code is filled if creating manually.").format(str(e))
            )


@frappe.whitelist()
def get_product_for_item(item):
    """Returns PEPL Product Master record for a given ERPNext Item.
    Used by Tender Management to auto-fetch product details."""

    product = frappe.db.get_value(
        "PEPL Product Master",
        {"linked_item": item},
        ["name", "product_name", "drawing_number", "pl_number",
         "current_drawing_revision", "current_drawing_file",
         "sector", "sub_sector", "product_type", "primary_customer", "hsn_sac_code"],
        as_dict=True
    )

    if not product:
        return None

    primary_spec = frappe.db.sql("""
        SELECT spec_title, reference_no, status
        FROM `tabPEPL Product Specification`
        WHERE parent = %s AND status = 'Active'
        ORDER BY creation ASC LIMIT 1
    """, product.name, as_dict=True)

    if primary_spec:
        product["primary_specification"] = primary_spec[0].spec_title
        product["primary_spec_reference"] = primary_spec[0].reference_no

    return product


@frappe.whitelist()
def sync_components_from_bom(product_name):
    """Sync assembly_components child table from linked BOM."""

    product = frappe.get_doc("PEPL Product Master", product_name)

    if not product.linked_bom:
        frappe.throw(_("No BOM linked. Set Linked BOM first or ensure linked Item has an active default BOM."))

    bom = frappe.get_doc("BOM", product.linked_bom)

    if not bom.items:
        frappe.throw(_("Linked BOM has no items"))

    product.assembly_components = []

    for bom_item in bom.items:
        product.append("assembly_components", {
            "component_type": "Simple Component (Item only)",
            "component_item": bom_item.item_code,
            "quantity": bom_item.qty,
            "uom": bom_item.uom,
            "is_critical": 0
        })

    product.save()
    return {"synced": len(bom.items)}
