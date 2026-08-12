"""Permanent PEPL Tender -> CST Cost Sheet synchronization.

Business rules
--------------
1. One PEPL CST Cost Sheet per PEPL Tender Item row.
2. The Tender Item row name is the authoritative relationship key.
3. Saving a Tender creates a missing CST automatically.
4. Later Tender saves update only Tender-owned CST snapshot fields.
5. Costing-owned values/components are never overwritten.
6. Direct database writes are used for backlinks to avoid recursive saves.
7. Existing CST costing data is protected if a Tender Item is changed.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, today


CST_DOCTYPE = "PEPL CST Cost Sheet"
TENDER_DOCTYPE = "PEPL Tender"
TENDER_ITEM_DOCTYPE = "PEPL Tender Item"
PRODUCT_DOCTYPE = "PEPL Product Master"


def _make_tender_item_key(tender_name, tender_item_name):
    if not tender_name or not tender_item_name:
        return None

    return "{}::{}".format(
        tender_name,
        tender_item_name,
    )


def _get_item_label(item_code):
    if not item_code:
        return _("Item")

    return (
        frappe.db.get_value(
            "Item",
            item_code,
            "item_name",
        )
        or item_code
    )


def _get_product_for_tender_item(tender, item_row):
    """Return one unambiguous Product Master for a Tender Item.

    Priority is:
    1. Customer + Sector + Item, where fields exist.
    2. Sector + Item, where field exists.
    3. Customer + Item, where field exists.
    4. Item only, provided exactly one Product Master exists.
    """

    if not item_row.item:
        frappe.throw(
            _(
                "Tender Item row {0} does not contain an Item."
            ).format(item_row.idx)
        )

    product_meta = frappe.get_meta(PRODUCT_DOCTYPE)

    candidate_filters = []

    if (
        tender.customer
        and tender.sector
        and product_meta.has_field("primary_customer")
        and product_meta.has_field("sector")
    ):
        candidate_filters.append(
            {
                "linked_item": item_row.item,
                "primary_customer": tender.customer,
                "sector": tender.sector,
            }
        )

    if (
        tender.sector
        and product_meta.has_field("sector")
    ):
        candidate_filters.append(
            {
                "linked_item": item_row.item,
                "sector": tender.sector,
            }
        )

    if (
        tender.customer
        and product_meta.has_field("primary_customer")
    ):
        candidate_filters.append(
            {
                "linked_item": item_row.item,
                "primary_customer": tender.customer,
            }
        )

    candidate_filters.append(
        {
            "linked_item": item_row.item,
        }
    )

    checked = set()

    for filters in candidate_filters:
        signature = tuple(
            sorted(filters.items())
        )

        if signature in checked:
            continue

        checked.add(signature)

        matches = frappe.get_all(
            PRODUCT_DOCTYPE,
            filters=filters,
            fields=["name"],
            order_by="name asc",
            limit_page_length=3,
        )

        if len(matches) == 1:
            return matches[0].name

        if len(matches) > 1:
            frappe.throw(
                _(
                    "Automatic CST creation is ambiguous for Tender "
                    "Item row {0}, Item {1}. More than one PEPL "
                    "Product Master matches: {2}. Resolve the Product "
                    "Master mapping before saving this Tender."
                ).format(
                    item_row.idx,
                    frappe.bold(item_row.item),
                    ", ".join(
                        row.name
                        for row in matches
                    ),
                )
            )

    frappe.throw(
        _(
            "Cannot automatically create a CST for Tender Item "
            "row {0}, Item {1}, because no PEPL Product Master "
            "is linked to this Item. Create/fix the Product Master "
            "mapping and save the Tender again."
        ).format(
            item_row.idx,
            frappe.bold(item_row.item),
        )
    )


def _get_tender_snapshot(tender, item_row, product_name):
    """Return fields owned by the Tender and safe to synchronize into CST."""

    item_label = _get_item_label(
        item_row.item
    )

    cst_title = "{} - {}".format(
        tender.tender_title
        or tender.name,
        item_label,
    )

    return {
        "linked_product":
            product_name,
        "linked_item":
            item_row.item,
        "linked_tender":
            tender.name,
        "linked_tender_item":
            item_row.name,
        "tender_item_key":
            _make_tender_item_key(
                tender.name,
                item_row.name,
            ),
        "customer":
            tender.customer,
        "sector":
            tender.sector,
        "cst_title":
            cst_title,
        "tender_nit_number":
            tender.nit_number,
        "tender_title":
            tender.tender_title,
        "tender_publication_date":
            tender.publication_date,
        "tender_bid_submission_deadline":
            tender.bid_submission_deadline,
        "tender_business_status":
            tender.status,
        "tender_item_quantity":
            flt(item_row.quantity),
        "tender_item_uom":
            item_row.uom,
        "tender_estimated_unit_price":
            flt(item_row.estimated_unit_price),
        "tender_estimated_total_value":
            flt(item_row.estimated_total_value),
        "tender_delivery_period_days":
            item_row.delivery_period_days,
    }


def _get_cst_link_data(cst_name):
    if not cst_name:
        return None

    if not frappe.db.exists(
        CST_DOCTYPE,
        cst_name,
    ):
        return None

    return frappe.db.get_value(
        CST_DOCTYPE,
        cst_name,
        [
            "name",
            "linked_tender",
            "linked_tender_item",
            "linked_item",
            "linked_product",
            "status",
            "final_bid_price",
            "total_components_cost",
            "linked_bom",
        ],
        as_dict=True,
    )


def _get_existing_cst_for_tender_item(
    tender,
    item_row,
):
    """Find the one canonical CST for this Tender Item.

    Existing child-row backlink is preferred. Legacy linked Tender/Item
    relationships are also adopted. Multiple matches are rejected.
    """

    if item_row.linked_cost_sheet:
        linked = _get_cst_link_data(
            item_row.linked_cost_sheet
        )

        if linked:
            if (
                linked.linked_tender
                and linked.linked_tender
                != tender.name
            ):
                frappe.throw(
                    _(
                        "Tender Item row {0} points to Cost Sheet "
                        "{1}, but that Cost Sheet belongs to Tender "
                        "{2}."
                    ).format(
                        item_row.idx,
                        linked.name,
                        linked.linked_tender,
                    )
                )

            if (
                linked.linked_tender_item
                and linked.linked_tender_item
                != item_row.name
            ):
                frappe.throw(
                    _(
                        "Tender Item row {0} points to Cost Sheet "
                        "{1}, but that Cost Sheet is already linked "
                        "to another Tender Item row {2}."
                    ).format(
                        item_row.idx,
                        linked.name,
                        linked.linked_tender_item,
                    )
                )

            return linked.name

        # Broken child-table backlink: clear it safely.
        frappe.db.set_value(
            TENDER_ITEM_DOCTYPE,
            item_row.name,
            "linked_cost_sheet",
            None,
            update_modified=False,
        )
        item_row.linked_cost_sheet = None

    direct_matches = frappe.get_all(
        CST_DOCTYPE,
        filters={
            "linked_tender":
                tender.name,
            "linked_tender_item":
                item_row.name,
        },
        fields=["name"],
        order_by="creation asc",
        limit_page_length=0,
    )

    if len(direct_matches) > 1:
        frappe.throw(
            _(
                "Duplicate CST records already exist for Tender "
                "{0}, Tender Item row {1}: {2}. Resolve these "
                "duplicates before continuing."
            ).format(
                tender.name,
                item_row.name,
                ", ".join(
                    row.name
                    for row in direct_matches
                ),
            )
        )

    if direct_matches:
        return direct_matches[0].name

    # Legacy adoption:
    # Some earlier CSTs may have linked_tender + linked_item but no
    # linked_tender_item. Adopt only when both sides are unambiguous.
    same_item_rows = [
        row
        for row in tender.items or []
        if row.item == item_row.item
    ]

    if len(same_item_rows) == 1:
        legacy_candidates = frappe.get_all(
            CST_DOCTYPE,
            filters={
                "linked_tender":
                    tender.name,
                "linked_item":
                    item_row.item,
            },
            fields=[
                "name",
                "linked_tender_item",
            ],
            order_by="creation asc",
            limit_page_length=0,
        )

        legacy_candidates = [
            row
            for row in legacy_candidates
            if not row.linked_tender_item
        ]

        if len(legacy_candidates) == 1:
            return legacy_candidates[0].name

        if len(legacy_candidates) > 1:
            frappe.throw(
                _(
                    "Multiple legacy CST records exist for Tender "
                    "{0}, Item {1}: {2}. They cannot be adopted "
                    "automatically."
                ).format(
                    tender.name,
                    item_row.item,
                    ", ".join(
                        row.name
                        for row
                        in legacy_candidates
                    ),
                )
            )

    return None


def _assert_existing_cst_can_follow_item(
    cst_name,
    tender,
    item_row,
):
    """Prevent an existing costed CST from being silently moved to another Item."""

    cst_data = _get_cst_link_data(
        cst_name
    )

    if not cst_data:
        return

    if (
        not cst_data.linked_item
        or cst_data.linked_item
        == item_row.item
    ):
        return

    component_count = frappe.db.count(
        "PEPL CST Component",
        {
            "parent": cst_name,
            "parenttype": CST_DOCTYPE,
        },
    )

    has_costing_data = bool(
        component_count
        or flt(
            cst_data.total_components_cost
        )
        or flt(
            cst_data.final_bid_price
        )
        or cst_data.linked_bom
        or cst_data.status
        not in {
            None,
            "",
            "Draft",
        }
    )

    if has_costing_data:
        frappe.throw(
            _(
                "Tender Item row {0} was changed from Item {1} "
                "to {2}, but its linked Cost Sheet {3} already "
                "contains costing data. To protect costing history, "
                "do not repurpose this Cost Sheet. Restore the "
                "original Item or create a new Tender Item row."
            ).format(
                item_row.idx,
                cst_data.linked_item,
                item_row.item,
                cst_name,
            )
        )


def _create_cst(
    tender,
    item_row,
    product_name,
):
    values = _get_tender_snapshot(
        tender,
        item_row,
        product_name,
    )

    cst = frappe.new_doc(
        CST_DOCTYPE
    )

    for fieldname, value in values.items():
        setattr(
            cst,
            fieldname,
            value,
        )

    cst.status = "Draft"
    cst.costing_date = today()
    cst.prepared_by = (
        frappe.session.user
        if frappe.session.user
        and frappe.session.user != "Guest"
        else None
    )

    cst.flags.pepl_created_from_tender = True

    cst.insert(
        ignore_permissions=True
    )

    return cst.name


def _update_cst_from_tender(
    cst_name,
    tender,
    item_row,
    product_name,
):
    """Synchronize only Tender-owned values.

    This intentionally does not save the CST Document, so costing
    validations/component history calculations are not re-run merely
    because a Tender was saved.
    """

    _assert_existing_cst_can_follow_item(
        cst_name,
        tender,
        item_row,
    )

    values = _get_tender_snapshot(
        tender,
        item_row,
        product_name,
    )

    frappe.db.set_value(
        CST_DOCTYPE,
        cst_name,
        values,
        update_modified=True,
    )


def _set_tender_cost_sheet_summary(
    tender,
    linked_cost_sheets,
):
    linked_cost_sheets = [
        value
        for value in linked_cost_sheets
        if value
    ]

    primary = (
        linked_cost_sheets[0]
        if linked_cost_sheets
        else None
    )

    count = len(
        linked_cost_sheets
    )

    tender.primary_cost_sheet = primary
    tender.cost_sheet_count = count

    if frappe.db.has_column(
        TENDER_DOCTYPE,
        "primary_cost_sheet",
    ):
        frappe.db.set_value(
            TENDER_DOCTYPE,
            tender.name,
            {
                "primary_cost_sheet":
                    primary,
                "cost_sheet_count":
                    count,
            },
            update_modified=False,
        )


def _refresh_parent_cost_sheet_summary(
    tender_name,
):
    if not tender_name:
        return

    rows = frappe.get_all(
        TENDER_ITEM_DOCTYPE,
        filters={
            "parent":
                tender_name,
            "parenttype":
                TENDER_DOCTYPE,
            "parentfield":
                "items",
        },
        fields=[
            "idx",
            "linked_cost_sheet",
        ],
        order_by="idx asc",
        limit_page_length=0,
    )

    links = [
        row.linked_cost_sheet
        for row in rows
        if row.linked_cost_sheet
        and frappe.db.exists(
            CST_DOCTYPE,
            row.linked_cost_sheet,
        )
    ]

    primary = (
        links[0]
        if links
        else None
    )

    if frappe.db.has_column(
        TENDER_DOCTYPE,
        "primary_cost_sheet",
    ):
        frappe.db.set_value(
            TENDER_DOCTYPE,
            tender_name,
            {
                "primary_cost_sheet":
                    primary,
                "cost_sheet_count":
                    len(links),
            },
            update_modified=False,
        )


def sync_tender_cost_sheets(tender):
    """Create/update exactly one CST for every Tender Item row."""

    if not tender.name:
        return {
            "created": [],
            "updated": [],
            "linked": [],
        }

    if cint(tender.docstatus) == 2:
        return {
            "created": [],
            "updated": [],
            "linked": [],
        }

    syncing = getattr(
        frappe.flags,
        "pepl_tender_cst_syncing",
        set(),
    )

    if not isinstance(
        syncing,
        set,
    ):
        syncing = set()

    if tender.name in syncing:
        return {
            "created": [],
            "updated": [],
            "linked": [],
        }

    syncing.add(
        tender.name
    )
    frappe.flags.pepl_tender_cst_syncing = syncing

    created = []
    updated = []
    linked = []

    try:
        if not tender.items:
            _set_tender_cost_sheet_summary(
                tender,
                [],
            )

            return {
                "created": [],
                "updated": [],
                "linked": [],
            }

        for item_row in tender.items:
            if not item_row.item:
                continue

            product_name = (
                _get_product_for_tender_item(
                    tender,
                    item_row,
                )
            )

            cst_name = (
                _get_existing_cst_for_tender_item(
                    tender,
                    item_row,
                )
            )

            if cst_name:
                _update_cst_from_tender(
                    cst_name,
                    tender,
                    item_row,
                    product_name,
                )
                updated.append(
                    cst_name
                )
            else:
                cst_name = _create_cst(
                    tender,
                    item_row,
                    product_name,
                )
                created.append(
                    cst_name
                )

            if (
                item_row.linked_cost_sheet
                != cst_name
            ):
                item_row.linked_cost_sheet = (
                    cst_name
                )

                frappe.db.set_value(
                    TENDER_ITEM_DOCTYPE,
                    item_row.name,
                    "linked_cost_sheet",
                    cst_name,
                    update_modified=False,
                )

            linked.append(
                cst_name
            )

        _set_tender_cost_sheet_summary(
            tender,
            linked,
        )

        return {
            "created": created,
            "updated": updated,
            "linked": linked,
        }

    finally:
        syncing.discard(
            tender.name
        )


def validate_cst_tender_link(cst):
    """Validate and normalize a CST -> Tender Item relationship."""

    if not cst.linked_tender:
        cst.tender_item_key = None
        return

    if not cst.linked_tender_item:
        frappe.throw(
            _(
                "Linked Tender Item Row is required when "
                "Linked Tender is set."
            )
        )

    tender = frappe.get_doc(
        TENDER_DOCTYPE,
        cst.linked_tender,
    )

    item_row = next(
        (
            row
            for row in tender.items or []
            if row.name
            == cst.linked_tender_item
        ),
        None,
    )

    if not item_row:
        frappe.throw(
            _(
                "Tender Item row {0} does not belong "
                "to Tender {1}."
            ).format(
                cst.linked_tender_item,
                cst.linked_tender,
            )
        )

    product_name = (
        _get_product_for_tender_item(
            tender,
            item_row,
        )
    )

    key = _make_tender_item_key(
        tender.name,
        item_row.name,
    )

    filters = {
        "linked_tender":
            tender.name,
        "linked_tender_item":
            item_row.name,
    }

    duplicates = frappe.get_all(
        CST_DOCTYPE,
        filters=filters,
        fields=["name"],
        order_by="creation asc",
        limit_page_length=0,
    )

    duplicates = [
        row
        for row in duplicates
        if row.name != cst.name
    ]

    if duplicates:
        frappe.throw(
            _(
                "Tender {0}, Tender Item row {1} already has "
                "Cost Sheet {2}. One Cost Sheet per Tender Item "
                "is enforced."
            ).format(
                tender.name,
                item_row.name,
                duplicates[0].name,
            )
        )

    snapshot = _get_tender_snapshot(
        tender,
        item_row,
        product_name,
    )

    for fieldname, value in snapshot.items():
        setattr(
            cst,
            fieldname,
            value,
        )

    cst.tender_item_key = key


def link_cst_to_tender(cst):
    """Write CST backlinks without calling Tender.save()."""

    if (
        not cst.linked_tender
        or not cst.linked_tender_item
        or not cst.name
    ):
        return

    old_doc = (
        cst.get_doc_before_save()
        if not cst.is_new()
        else None
    )

    if (
        old_doc
        and old_doc.linked_tender_item
        and (
            old_doc.linked_tender_item
            != cst.linked_tender_item
            or old_doc.linked_tender
            != cst.linked_tender
        )
    ):
        old_row = frappe.db.get_value(
            TENDER_ITEM_DOCTYPE,
            old_doc.linked_tender_item,
            [
                "name",
                "parent",
                "linked_cost_sheet",
            ],
            as_dict=True,
        )

        if (
            old_row
            and old_row.linked_cost_sheet
            == cst.name
        ):
            frappe.db.set_value(
                TENDER_ITEM_DOCTYPE,
                old_row.name,
                "linked_cost_sheet",
                None,
                update_modified=False,
            )

            _refresh_parent_cost_sheet_summary(
                old_row.parent
            )

    linked_row = frappe.db.get_value(
        TENDER_ITEM_DOCTYPE,
        cst.linked_tender_item,
        [
            "name",
            "parent",
            "linked_cost_sheet",
        ],
        as_dict=True,
    )

    if not linked_row:
        return

    if (
        linked_row.parent
        != cst.linked_tender
    ):
        frappe.throw(
            _(
                "Tender Item row {0} does not belong "
                "to Tender {1}."
            ).format(
                cst.linked_tender_item,
                cst.linked_tender,
            )
        )

    tender_item_values = {
        "linked_cost_sheet":
            cst.name,
        "our_bid_unit_price":
            flt(cst.final_bid_price),
    }

    quantity = frappe.db.get_value(
        TENDER_ITEM_DOCTYPE,
        linked_row.name,
        "quantity",
    ) or 0

    tender_item_values[
        "our_bid_total_value"
    ] = (
        flt(quantity)
        * flt(cst.final_bid_price)
    )

    frappe.db.set_value(
        TENDER_ITEM_DOCTYPE,
        linked_row.name,
        tender_item_values,
        update_modified=False,
    )

    _refresh_parent_cost_sheet_summary(
        cst.linked_tender
    )


@frappe.whitelist()
def backfill_existing_tender_cost_sheets(
    tender_name=None,
    fail_fast=False,
):
    """Backfill missing Tender -> CST relationships safely.

    Each Tender is isolated with a database savepoint so one bad legacy
    record does not corrupt another Tender during the migration/backfill.
    """

    fail_fast = cint(
        fail_fast
    )

    if tender_name:
        if not frappe.db.exists(
            TENDER_DOCTYPE,
            tender_name,
        ):
            frappe.throw(
                _(
                    "PEPL Tender {0} does not exist."
                ).format(
                    tender_name
                )
            )

        tender_names = [
            tender_name
        ]
    else:
        tender_names = frappe.get_all(
            TENDER_DOCTYPE,
            filters={
                "docstatus":
                    ["!=", 2],
            },
            pluck="name",
            order_by="creation asc",
            limit_page_length=0,
        )

    result = {
        "tenders_checked": 0,
        "created": [],
        "updated": [],
        "failed": [],
    }

    for index, name in enumerate(
        tender_names,
        start=1,
    ):
        result["tenders_checked"] += 1

        savepoint = (
            "pepl_tender_cst_{}"
            .format(index)
        )

        frappe.db.savepoint(
            savepoint
        )

        try:
            tender = frappe.get_doc(
                TENDER_DOCTYPE,
                name,
            )

            sync_result = (
                sync_tender_cost_sheets(
                    tender
                )
            )

            result["created"].extend(
                [
                    {
                        "tender":
                            name,
                        "cost_sheet":
                            cst_name,
                    }
                    for cst_name
                    in sync_result.get(
                        "created",
                        [],
                    )
                ]
            )

            result["updated"].extend(
                [
                    {
                        "tender":
                            name,
                        "cost_sheet":
                            cst_name,
                    }
                    for cst_name
                    in sync_result.get(
                        "updated",
                        [],
                    )
                ]
            )

        except Exception as exc:
            frappe.db.rollback(
                save_point=savepoint
            )

            failure = {
                "tender":
                    name,
                "error":
                    str(exc),
            }

            result["failed"].append(
                failure
            )

            frappe.log_error(
                message=frappe.get_traceback(),
                title=(
                    "PEPL Tender CST Backfill: {}"
                    .format(name)
                ),
            )

            if fail_fast:
                raise

    return result


def clear_cst_from_tender(doc, method=None):
    """Safely clear Tender backlinks when a CST is deleted.

    This deliberately uses direct database writes instead of Tender.save()
    so CST deletion cannot trigger Tender -> CST recreation or alter the
    Tender business status.
    """

    tender_name = (
        doc.linked_tender
        or ""
    ).strip()

    tender_item_name = (
        doc.linked_tender_item
        or ""
    ).strip()

    if (
        not tender_name
        or not tender_item_name
    ):
        return

    row = frappe.db.get_value(
        TENDER_ITEM_DOCTYPE,
        tender_item_name,
        [
            "name",
            "parent",
            "parenttype",
            "parentfield",
            "linked_cost_sheet",
        ],
        as_dict=True,
    )

    if not row:
        return

    if (
        row.parent != tender_name
        or row.parenttype != TENDER_DOCTYPE
        or row.parentfield != "items"
    ):
        return

    if row.linked_cost_sheet == doc.name:
        frappe.db.set_value(
            TENDER_ITEM_DOCTYPE,
            tender_item_name,
            {
                "linked_cost_sheet": None,
                "our_bid_unit_price": 0,
                "our_bid_total_value": 0,
            },
            update_modified=False,
        )

    _refresh_parent_cost_sheet_summary(
        tender_name
    )
