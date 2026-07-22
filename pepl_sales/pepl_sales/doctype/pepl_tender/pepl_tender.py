
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, today


FINAL_OUTCOMES = {"Won", "Partially Won", "Lost", "Cancelled"}


def parse_rank_number(rank):
    """Return numeric rank from values such as L1, L2, L15.

    Non-numeric source values such as Disqualified or Mixed return 0.
    """
    value = (rank or "").strip().upper()
    match = re.fullmatch(r"L\s*0*(\d+)", value)
    return int(match.group(1)) if match else 0


def get_primary_evaluated_price(row, item_row=None):
    """Return the correct comparison value for a competitor row."""
    basis = (
        row.evaluation_basis
        or getattr(item_row, "evaluation_basis", None)
        or ""
    )

    total_value_basis = basis in {"Total Bid Value", "Item Total Value"}

    if total_value_basis and flt(row.total_bid_value) > 0:
        return flt(row.total_bid_value)

    if flt(row.evaluated_unit_rate) > 0:
        return flt(row.evaluated_unit_rate)

    if flt(row.total_bid_value) > 0:
        return flt(row.total_bid_value)

    if flt(row.calculated_unit_rate) > 0:
        return flt(row.calculated_unit_rate)

    return 0


class PEPLTender(Document):
    def autoname(self):
        from frappe.model.naming import make_autoname

        self.tender_no = make_autoname("TND-.YYYY.-.####")
        self.name = self.tender_no

    def validate(self):
        # Auto-set sub-sector from customer group if not already set
        if self.customer_group and not self.sub_sector:
            cg = self.customer_group
            mapping = {
                "Railways - Loco": "Railways - Loco",
                "Railways - Coaches": "Railways - Coaches",
                "Railways - Zonal": "Railways - Zonal",
                "Defence - MIL": "Defence - MIL",
                "Defence - YIL": "Defence - YIL",
                "Defence - AWEIL": "Defence - AWEIL",
                "Defence - Private": "Defence - Private",
                "Private Sector": "Private Sector",
                "PSU": "PSU",
            }
            if cg in mapping:
                self.sub_sector = mapping[cg]

        # Auto-set sector from customer group
        if self.customer_group and not self.sector:
            if "Railways" in self.customer_group:
                self.sector = "Railways"
            elif "Defence" in self.customer_group:
                self.sector = "Defence"
            elif "Private" in self.customer_group:
                self.sector = "Private"
            else:
                self.sector = "Others"

        # Enforce mutually exclusive EMD / Bid Securing choices server-side.
        if self.emd_required and self.bid_securing_declaration:
            frappe.throw(
                _(
                    "EMD Required and Bid Securing Declaration cannot both "
                    "be selected."
                )
            )

        if self.emd_required:
            if flt(self.emd_amount) <= 0:
                frappe.throw(_("EMD Amount must be greater than zero."))
            if not self.emd_mode:
                frappe.throw(_("EMD Mode is required when EMD is required."))

        # Auto-fetch vendor approval stage and drawing/spec for each item
        if self.items:
            for item_row in self.items:
                if item_row.item and self.sector:
                    self._fetch_item_details(item_row)

        # Calculate competitor analysis before parent summaries/status.
        self._calculate_competitor_analysis()
        self._apply_award_result_fallbacks()
        self._calculate_summary()
        self._update_overall_status()
        self._validate_outcomes()
        self._build_outcome_summary()

        # Process PO Schedule: recalc totals, flag won-list status, sum parent total
        self._process_po_schedule()

        # Validation: bid deadline check
        if self.bid_submission_deadline and self.is_new():
            if getdate(self.bid_submission_deadline) < getdate(today()):
                frappe.msgprint(
                    _("Bid deadline {0} is in the past — please verify").format(
                        self.bid_submission_deadline
                    ),
                    indicator="orange",
                    alert=True,
                )


    def before_update_after_submit(self):
        """Recalculate PO-derived fields during permitted post-submit edits.

        Frappe uses the update-after-submit lifecycle for fields marked
        allow_on_submit. Keeping this logic here ensures that PO Schedule
        flags, line totals and the parent PO total are recalculated on the
        server even when client-side events do not run.
        """
        self._process_po_schedule()



    def before_submit(self):
        """Validate that the Tender is ready for final submission."""
        final_statuses = {
            "Won",
            "Partially Won",
            "Order Received",
            "Lost",
            "No Bid",
        }

        if self.status not in final_statuses:
            frappe.throw(
                _(
                    "PEPL Tender can be submitted only after its final outcome "
                    "is recorded. Current status: {0}. The business status "
                    "'Submitted' means the bid was sent to the customer and "
                    "must remain editable until the final outcome is known."
                ).format(self.status or _("Not Set"))
            )

        if not self.items:
            frappe.throw(
                _("At least one Tender Item is required before submission.")
            )

        if self.status == "No Bid":
            if self.bid_decision != "No Bid":
                frappe.throw(
                    _(
                        "Bid Decision must be set to No Bid before submitting "
                        "a No Bid Tender."
                    )
                )
            if not self.no_bid_reason:
                frappe.throw(
                    _("No Bid Reason is required before submission.")
                )
        else:
            if not self.outcome_date:
                frappe.throw(
                    _("Outcome Date is required before submission.")
                )

            pending_rows = [
                str(index)
                for index, row in enumerate(self.items, start=1)
                if not row.outcome or row.outcome == "Pending"
            ]
            if pending_rows:
                frappe.throw(
                    _(
                        "Tender Item outcome is Pending in row(s): {0}."
                    ).format(", ".join(pending_rows))
                )

        if self.status == "Order Received":
            if not self.linked_sales_order:
                frappe.throw(
                    _(
                        "Linked Sales Order is required when Tender status is "
                        "Order Received."
                    )
                )
            if not frappe.db.exists(
                "Sales Order",
                self.linked_sales_order,
            ):
                frappe.throw(
                    _("Linked Sales Order {0} does not exist.").format(
                        self.linked_sales_order
                    )
                )

        # Recalculate and validate all final values immediately before submit.
        self._calculate_competitor_analysis()
        self._apply_award_result_fallbacks()
        self._calculate_summary()
        self._update_overall_status()
        self._validate_outcomes()
        self._build_outcome_summary()
        self._process_po_schedule()

    def on_submit(self):
        """Notify the user that the Tender is now a final record."""
        frappe.msgprint(
            _("PEPL Tender {0} has been submitted successfully.").format(
                self.name
            ),
            indicator="green",
            alert=True,
        )

    def before_cancel(self):
        """Prevent cancellation while a linked Sales Order is submitted."""
        if not self.linked_sales_order:
            return

        sales_order_docstatus = frappe.db.get_value(
            "Sales Order",
            self.linked_sales_order,
            "docstatus",
        )

        if sales_order_docstatus == 1:
            frappe.throw(
                _(
                    "Cannot cancel this Tender because linked Sales Order "
                    "{0} is submitted. Cancel the Sales Order first."
                ).format(self.linked_sales_order)
            )

    def on_cancel(self):
        """Keep the business status aligned with Frappe cancellation."""
        self.db_set("status", "Cancelled", update_modified=False)

    def _fetch_item_details(self, item_row):
        """Fetch drawing, spec, vendor approval stage, PL number for an item row."""
        if item_row.item:
            has_pl = frappe.db.has_column("Item", "custom_pl_no")
            has_drawing = frappe.db.has_column("Item", "custom_drawing_no")

            if has_pl or has_drawing:
                select_fields = ["name"]
                if has_pl:
                    select_fields.append("custom_pl_no")
                if has_drawing:
                    select_fields.append("custom_drawing_no")

                fields_str = ", ".join(select_fields)

                item_data = frappe.db.sql(
                    f"""
                    SELECT {fields_str}
                    FROM `tabItem`
                    WHERE name = %s
                    LIMIT 1
                    """,
                    item_row.item,
                    as_dict=True,
                )

                if item_data:
                    if has_pl and "custom_pl_no" in item_data[0]:
                        item_row.pl_no = item_data[0].custom_pl_no
                    if has_drawing and "custom_drawing_no" in item_data[0]:
                        item_row.drawing_no = item_data[0].custom_drawing_no

        product = frappe.db.get_value(
            "PEPL Product Master",
            {"linked_item": item_row.item},
            ["name", "current_drawing_revision", "drawing_number", "pl_number"],
            as_dict=True,
        )

        if product:
            item_row.current_drawing_revision = product.current_drawing_revision

            if not item_row.pl_no and product.pl_number:
                item_row.pl_no = product.pl_number

            if not item_row.drawing_no and product.drawing_number:
                item_row.drawing_no = product.drawing_number

            primary_spec = frappe.db.sql(
                """
                SELECT spec_title FROM `tabPEPL Product Specification`
                WHERE parent = %s AND status = 'Active'
                ORDER BY creation ASC LIMIT 1
                """,
                product.name,
                as_dict=True,
            )

            if primary_spec:
                item_row.current_specification = primary_spec[0].spec_title

        from pepl_sales.pepl_sales.doctype.vendor_approval_status.vendor_approval_status import (
            get_approval_status_for_item,
        )

        approval = get_approval_status_for_item(
            self.customer,
            item_row.item,
            self.sector,
        )

        item_row.vendor_approval_record = approval.get("name")
        item_row.vendor_approval_stage = approval.get("stage") or "No Record"
        item_row.vendor_approval_health = approval.get("health") or "Missing"
        item_row.vendor_approval_expiry = approval.get("expiry_date")
        item_row.vendor_approval_warning = approval.get("warning") or ""

    def _calculate_competitor_analysis(self):
        """Calculate competitor analysis from the parent competitor table."""
        competitor_rows = self.competitor_entries or []
        item_rows_by_code = {
            row.item: row
            for row in self.items or []
            if row.item
        }

        if competitor_rows and len(item_rows_by_code) > 1:
            missing_item_rows = [
                str(index)
                for index, row in enumerate(competitor_rows, start=1)
                if not row.get("item")
            ]
            if missing_item_rows:
                frappe.throw(
                    _(
                        "Competitor Entry row(s) {0}: Item is required when "
                        "the Tender contains multiple items."
                    ).format(", ".join(missing_item_rows))
                )

        for item_row in self.items or []:
            groups = {}
            rows_for_item = [
                row
                for row in competitor_rows
                if row.get("item") == item_row.item
                or (
                    len(item_rows_by_code) == 1
                    and not row.get("item")
                )
            ]

            for row in rows_for_item:
                self._calculate_competitor_row(row, item_row)

                group_key = (row.consignee or "").strip() or "__DEFAULT__"
                groups.setdefault(group_key, []).append(row)

            if not groups:
                self._clear_item_competitor_summary(item_row)
                continue

            group_summaries = []

            for group_key, rows in groups.items():
                summary = self._analyse_competitor_group(
                    group_key,
                    rows,
                    item_row,
                )
                if summary:
                    group_summaries.append(summary)

            self._apply_item_competitor_summary(
                item_row,
                group_summaries,
            )

    def _calculate_competitor_row(self, row, item_row):
        """Calculate one competitor row without overwriting official TUR."""
        rank_number = parse_rank_number(row.rank)
        row.rank_number = rank_number
        row.is_l1 = 1 if rank_number == 1 else 0

        discounted_basic = flt(row.basic_rate) * (
            1 - flt(row.unconditional_discount_percent) / 100
        )
        percentage_other_charges = (
            discounted_basic * flt(row.other_charges_percent) / 100
        )

        subtotal_before_gst = (
            discounted_basic
            + flt(row.packing_charges)
            + flt(row.freight)
            + flt(row.forwarding)
            + flt(row.other_charges_amount)
            + percentage_other_charges
        )

        gst_amount = subtotal_before_gst * flt(row.gst_percent) / 100
        row.calculated_unit_rate = subtotal_before_gst + gst_amount

        row.competitor_price = get_primary_evaluated_price(
            row,
            item_row,
        )

    def _analyse_competitor_group(self, group_key, rows, item_row):
        """Analyse a single consignee/evaluation group."""
        priced_rows = [
            row
            for row in rows
            if flt(row.competitor_price) > 0
        ]

        if not priced_rows:
            for row in rows:
                row.difference_from_pepl = 0
                row.difference_from_pepl_percent = 0
                row.difference_from_l1 = 0
                row.difference_from_l1_percent = 0
            return None

        pepl_rows = [row for row in priced_rows if row.is_pepl]
        if len(pepl_rows) > 1:
            frappe.throw(
                _(
                    "Only one PEPL bidder row is allowed per "
                    "Tender Item and Consignee group: {0}."
                ).format(
                    "Default"
                    if group_key == "__DEFAULT__"
                    else group_key
                )
            )

        pepl_row = pepl_rows[0] if pepl_rows else None

        explicit_l1 = [
            row
            for row in priced_rows
            if row.is_l1 or row.rank_number == 1
        ]
        l1_row = min(
            explicit_l1 or priced_rows,
            key=lambda row: flt(row.competitor_price),
        )

        winner_rows = [
            row
            for row in priced_rows
            if row.is_winner or row.buyer_selected
        ]
        effective_winners = winner_rows or [l1_row]
        winner_row = min(
            effective_winners,
            key=lambda row: flt(row.competitor_price),
        )
        winner_names = sorted(
            {
                row.competitor_name
                for row in effective_winners
                if row.competitor_name
            }
        )

        pepl_price = (
            flt(pepl_row.competitor_price)
            if pepl_row
            else 0
        )
        l1_price = flt(l1_row.competitor_price)

        for row in rows:
            row_price = flt(row.competitor_price)

            if pepl_price > 0 and row_price > 0:
                row.difference_from_pepl = row_price - pepl_price
                row.difference_from_pepl_percent = (
                    row.difference_from_pepl / pepl_price
                ) * 100
            else:
                row.difference_from_pepl = 0
                row.difference_from_pepl_percent = 0

            if l1_price > 0 and row_price > 0:
                row.difference_from_l1 = row_price - l1_price
                row.difference_from_l1_percent = (
                    row.difference_from_l1 / l1_price
                ) * 100
            else:
                row.difference_from_l1 = 0
                row.difference_from_l1_percent = 0

        quantity = max(
            [
                flt(row.consignee_quantity)
                for row in rows
                if flt(row.consignee_quantity) > 0
            ]
            or [flt(item_row.quantity) or 1]
        )

        basis = (
            winner_row.evaluation_basis
            or item_row.evaluation_basis
            or ""
        )
        is_total_value = basis in {
            "Total Bid Value",
            "Item Total Value",
        }

        winning_price = flt(winner_row.competitor_price)
        pepl_comparison_price = pepl_price

        if not is_total_value:
            winning_value = winning_price * quantity
            pepl_value = pepl_comparison_price * quantity
        else:
            winning_value = winning_price
            pepl_value = pepl_comparison_price

        return {
            "group_key": group_key,
            "winner_names": winner_names,
            "winner_name": (
                winner_names[0]
                if len(winner_names) == 1
                else "; ".join(winner_names)
            ),
            "winner_price": winning_price,
            "winner_value": winning_value,
            "lowest_price": l1_price,
            "pepl_price": pepl_comparison_price,
            "pepl_value": pepl_value,
            "pepl_rank": pepl_row.rank if pepl_row else "",
            "pepl_rank_number": pepl_row.rank_number if pepl_row else 0,
            "quantity": quantity,
            "basis": basis,
        }

    def _clear_item_competitor_summary(self, item_row):
        item_row.lowest_evaluated_price = 0
        item_row.winning_competitor = ""
        item_row.winning_price = 0
        item_row.our_price_difference = 0
        item_row.our_price_difference_percent = 0
        item_row.our_rank = ""
        item_row.our_rank_number = 0
        item_row.item_outcome_summary = ""

    def _apply_item_competitor_summary(
        self,
        item_row,
        group_summaries,
    ):
        if not group_summaries:
            self._clear_item_competitor_summary(item_row)
            return

        winner_names = sorted(
            {
                summary["winner_name"]
                for summary in group_summaries
                if summary["winner_name"]
            }
        )
        pepl_ranks = sorted(
            {
                summary["pepl_rank"]
                for summary in group_summaries
                if summary["pepl_rank"]
            },
            key=lambda value: parse_rank_number(value) or 999999,
        )
        rank_numbers = [
            summary["pepl_rank_number"]
            for summary in group_summaries
            if summary["pepl_rank_number"] > 0
        ]

        total_winning_value = sum(
            flt(summary["winner_value"])
            for summary in group_summaries
        )
        total_pepl_value = sum(
            flt(summary["pepl_value"])
            for summary in group_summaries
        )

        item_row.lowest_evaluated_price = min(
            flt(summary["lowest_price"])
            for summary in group_summaries
            if flt(summary["lowest_price"]) > 0
        )
        item_row.winning_price = total_winning_value
        item_row.winning_competitor = (
            winner_names[0]
            if len(winner_names) == 1
            else "Multiple / Consignee-wise"
        )

        if total_pepl_value > 0 and total_winning_value > 0:
            item_row.our_price_difference = (
                total_pepl_value - total_winning_value
            )
            item_row.our_price_difference_percent = (
                item_row.our_price_difference / total_winning_value
            ) * 100
        else:
            item_row.our_price_difference = 0
            item_row.our_price_difference_percent = 0

        if len(pepl_ranks) == 1:
            item_row.our_rank = pepl_ranks[0]
        elif len(pepl_ranks) > 1:
            item_row.our_rank = "Mixed"
        else:
            item_row.our_rank = ""

        item_row.our_rank_number = (
            rank_numbers[0]
            if rank_numbers and len(set(rank_numbers)) == 1
            else 0
        )

        group_count = len(group_summaries)
        rank_text = item_row.our_rank or "Not available"
        winner_text = item_row.winning_competitor or "Not available"

        item_row.item_outcome_summary = _(
            "Analysed {0} evaluation group(s). "
            "PEPL rank: {1}. Winner: {2}. "
            "Winning value: {3}. "
            "PEPL difference: {4} ({5:.2f}%)."
        ).format(
            group_count,
            rank_text,
            winner_text,
            frappe.format_value(
                item_row.winning_price,
                {"fieldtype": "Currency"},
            ),
            frappe.format_value(
                item_row.our_price_difference,
                {"fieldtype": "Currency"},
            ),
            flt(item_row.our_price_difference_percent),
        )

    def _apply_award_result_fallbacks(self):
        """Populate award value and rank when no priced result rows exist.

        Official competitor-analysis rows remain authoritative. This fallback
        is used only when the item is awarded but no calculated winning value
        or PEPL rank is available from those rows.
        """
        po_value_by_item = {}

        for schedule_row in self.po_schedule or []:
            if not schedule_row.item:
                continue

            line_total = (
                flt(schedule_row.po_quantity)
                * flt(schedule_row.po_rate)
            )

            po_value_by_item[schedule_row.item] = (
                flt(po_value_by_item.get(schedule_row.item))
                + line_total
            )

        is_explicit_l1_win = (
            self.win_reason == "L1 / Lowest Evaluated Price"
        )

        for item_row in self.items or []:
            if item_row.outcome not in {"Won", "Partially Won"}:
                continue

            awarded_quantity = self._get_awarded_quantity(item_row)

            if awarded_quantity <= 0:
                continue

            # Competitor analysis remains authoritative whenever it produced
            # an evaluated winning value.
            if flt(item_row.winning_price) <= 0:
                po_value = flt(
                    po_value_by_item.get(item_row.item)
                )

                if po_value > 0:
                    item_row.winning_price = po_value
                elif flt(item_row.our_bid_unit_price) > 0:
                    item_row.winning_price = (
                        awarded_quantity
                        * flt(item_row.our_bid_unit_price)
                    )

            # A Won Tender is not automatically L1. Derive L1 only when the
            # explicitly selected Win Reason confirms that result.
            if not item_row.our_rank and is_explicit_l1_win:
                item_row.our_rank = "L1"
                item_row.our_rank_number = 1

            if (
                not item_row.winning_competitor
                and item_row.outcome in {"Won", "Partially Won"}
            ):
                item_row.winning_competitor = "PEPL"

            if (
                not item_row.item_outcome_summary
                and flt(item_row.winning_price) > 0
            ):
                item_row.item_outcome_summary = _(
                    "Awarded to PEPL. Awarded quantity: {0}. "
                    "Awarded value: {1}. PEPL rank: {2}."
                ).format(
                    awarded_quantity,
                    frappe.format_value(
                        item_row.winning_price,
                        {"fieldtype": "Currency"},
                    ),
                    item_row.our_rank or _("Not recorded"),
                )

    def _calculate_summary(self):
        """Server-side recalculation of Tender totals and outcome counts."""
        if not self.items:
            self.total_estimated_value = 0
            self.total_bid_value = 0
            self.items_won = 0
            self.items_lost = 0
            self.win_rate = 0
            return

        for item in self.items:
            qty = flt(item.quantity)
            est_unit = flt(item.estimated_unit_price)
            our_unit = flt(item.our_bid_unit_price)

            item.estimated_total_value = qty * est_unit
            item.our_bid_total_value = qty * our_unit

        self.total_estimated_value = sum(
            flt(item.estimated_total_value)
            for item in self.items
        )
        self.total_bid_value = sum(
            flt(item.our_bid_total_value)
            for item in self.items
        )

        self.items_won = sum(
            1
            for item in self.items
            if item.outcome in {"Won", "Partially Won"}
        )
        self.items_lost = sum(
            1
            for item in self.items
            if item.outcome == "Lost"
        )

        decided_items = [
            item
            for item in self.items
            if item.outcome in FINAL_OUTCOMES
        ]

        if decided_items:
            won_weight = sum(
                1
                if item.outcome == "Won"
                else flt(item.award_share_percent) / 100
                if item.outcome == "Partially Won"
                else 0
                for item in decided_items
            )
            self.win_rate = (
                won_weight / len(decided_items)
            ) * 100
        else:
            self.win_rate = 0

    def _update_overall_status(self):
        """Derive Tender status from fully decided item outcomes."""
        if self.status == "Order Received" or not self.items:
            return

        outcomes = [item.outcome for item in self.items]

        if not outcomes or any(
            outcome in {None, "", "Pending"}
            for outcome in outcomes
        ):
            return

        if all(outcome == "Won" for outcome in outcomes):
            self.status = "Won"
        elif all(outcome == "Lost" for outcome in outcomes):
            self.status = "Lost"
        elif all(outcome == "Cancelled" for outcome in outcomes):
            self.status = "Cancelled"
        elif (
            "Partially Won" in outcomes
            or (
                any(outcome == "Won" for outcome in outcomes)
                and any(
                    outcome in {"Lost", "Cancelled"}
                    for outcome in outcomes
                )
            )
        ):
            self.status = "Partially Won"

    def _validate_outcomes(self):
        """Enforce essential item- and Tender-level outcome information."""
        for index, item in enumerate(self.items or [], start=1):
            if item.outcome == "Lost":
                if not item.item_loss_category:
                    frappe.throw(
                        _(
                            "Tender Item row {0}: Item Loss Category "
                            "is required for a Lost item."
                        ).format(index)
                    )
                if not item.item_loss_reason:
                    frappe.throw(
                        _(
                            "Tender Item row {0}: Item Loss Reason "
                            "is required for a Lost item."
                        ).format(index)
                    )

            if item.outcome == "Partially Won":
                if (
                    flt(item.awarded_quantity) <= 0
                    and flt(item.award_share_percent) <= 0
                ):
                    frappe.throw(
                        _(
                            "Tender Item row {0}: enter Awarded Quantity "
                            "or Award Share % for a Partially Won item."
                        ).format(index)
                    )
                if not item.item_loss_category:
                    frappe.throw(
                        _(
                            "Tender Item row {0}: Item Loss Category "
                            "is required for a Partially Won item."
                        ).format(index)
                    )
                if not item.item_loss_reason:
                    frappe.throw(
                        _(
                            "Tender Item row {0}: Item Loss Reason "
                            "is required for a Partially Won item."
                        ).format(index)
                    )

        if self.status == "Lost":
            if self.linked_sales_order:
                frappe.throw(
                    _(
                        "A Lost Tender cannot remain linked to "
                        "Sales Order {0}."
                    ).format(self.linked_sales_order)
                )
            if not self.outcome_date:
                frappe.throw(_("Outcome Date is required for a Lost Tender."))
            if not self.loss_reason:
                frappe.throw(_("Loss Category is required for a Lost Tender."))
            if not self.detailed_loss_reason:
                frappe.throw(
                    _("Detailed Loss Reason is required for a Lost Tender.")
                )

        if self.status == "Won":
            if not self.outcome_date:
                frappe.throw(_("Outcome Date is required for a Won Tender."))
            if not any(
                item.outcome == "Won"
                for item in self.items or []
            ):
                frappe.throw(
                    _("At least one Tender Item must be marked Won.")
                )
            if not self.win_reason:
                frappe.throw(_("Win Reason is required for a Won Tender."))
            has_pepl_bid = any(
                flt(item.our_bid_total_value) > 0
                or any(
                    row.is_pepl
                    and flt(row.competitor_price) > 0
                    and (row.get("item") == item.item or not row.get("item"))
                    for row in self.competitor_entries or []
                )
                for item in self.items or []
            )
            if not has_pepl_bid:
                frappe.throw(
                    _(
                        "Record the PEPL bid value or mark one priced "
                        "competitor row as Is PEPL before finalising a win."
                    )
                )

        if self.status == "Partially Won":
            if not self.outcome_date:
                frappe.throw(
                    _("Outcome Date is required for a Partially Won Tender.")
                )
            if not any(
                item.outcome in {"Won", "Partially Won"}
                for item in self.items or []
            ):
                frappe.throw(
                    _(
                        "At least one Tender Item must be Won "
                        "or Partially Won."
                    )
                )

            has_partial_loss = any(
                item.outcome in {"Lost", "Cancelled"}
                or (
                    item.outcome == "Partially Won"
                    and (
                        0 < flt(item.award_share_percent) < 100
                        or (
                            flt(item.awarded_quantity) > 0
                            and flt(item.quantity) > 0
                            and flt(item.awarded_quantity)
                            < flt(item.quantity)
                        )
                    )
                )
                for item in self.items or []
            )
            if not has_partial_loss:
                frappe.throw(
                    _(
                        "A Partially Won Tender must include a Lost/Cancelled "
                        "item or an award share/quantity below 100%."
                    )
                )
            if not self.win_reason:
                frappe.throw(
                    _("Win Reason is required for a Partially Won Tender.")
                )
            if not self.loss_reason:
                frappe.throw(
                    _("Loss Category is required for a Partially Won Tender.")
                )
            if not self.detailed_loss_reason:
                frappe.throw(
                    _(
                        "Detailed Loss Reason is required for a "
                        "Partially Won Tender."
                    )
                )

    def _build_outcome_summary(self):
        """Create a concise parent-level outcome summary."""
        if self.status not in {
            "Won",
            "Partially Won",
            "Lost",
            "Cancelled",
        }:
            self.outcome_summary = ""
            self.competitor_analysis_completed = 0
            return

        analysed_items = [
            item
            for item in self.items or []
            if (
                flt(item.winning_price) > 0
                or item.our_rank
                or item.winning_competitor
                or any(
                    row.get("item") == item.item
                    or (
                        len(self.items or []) == 1
                        and not row.get("item")
                    )
                    for row in self.competitor_entries or []
                )
            )
        ]

        winning_names = sorted(
            {
                item.winning_competitor
                for item in analysed_items
                if item.winning_competitor
            }
        )

        ranks = sorted(
            {
                item.our_rank
                for item in analysed_items
                if item.our_rank
            },
            key=lambda value: parse_rank_number(value) or 999999,
        )

        self.winning_competitor = (
            winning_names[0]
            if len(winning_names) == 1
            else "Multiple / Item-wise"
            if winning_names
            else self.winning_competitor
        )
        self.our_overall_rank = (
            ranks[0]
            if len(ranks) == 1
            else "Mixed"
            if ranks
            else ""
        )
        self.winning_price = sum(
            flt(item.winning_price)
            for item in analysed_items
        )

        details = [
            _("Tender outcome: {0}.").format(self.status),
            _("Items Won/Partially Won: {0}.").format(self.items_won),
            _("Items Lost: {0}.").format(self.items_lost),
        ]

        if self.our_overall_rank:
            details.append(
                _("PEPL overall rank: {0}.").format(
                    self.our_overall_rank
                )
            )
        if self.winning_competitor:
            details.append(
                _("Winning competitor: {0}.").format(
                    self.winning_competitor
                )
            )
        if self.loss_reason:
            details.append(
                _("Loss category: {0}.").format(self.loss_reason)
            )
        if self.win_reason:
            details.append(
                _("Win reason: {0}.").format(self.win_reason)
            )

        self.outcome_summary = " ".join(details)

        analysis_items = [
            item
            for item in self.items or []
            if item.outcome in {"Won", "Partially Won", "Lost"}
        ]
        self.competitor_analysis_completed = 1 if (
            analysis_items
            and all(
                any(
                    row.is_pepl
                    and flt(row.competitor_price) > 0
                    and (
                        row.get("item") == item.item
                        or (len(self.items or []) == 1 and not row.get("item"))
                    )
                    for row in self.competitor_entries or []
                )
                for item in analysis_items
            )
        ) else 0

    def _process_po_schedule(self):
        """Recalculate PO Schedule flags, identifiers, totals and parent total."""
        if not self.po_schedule:
            self.po_amount_received = 0
            return

        tender_items = {
            row.item: row
            for row in self.items or []
            if row.item
        }

        total = 0
        for schedule_row in self.po_schedule:
            tender_item = tender_items.get(schedule_row.item)

            is_awarded_item = bool(
                tender_item
                and tender_item.outcome in {"Won", "Partially Won"}
                and self._get_awarded_quantity(tender_item) > 0
            )
            schedule_row.is_in_won_list = 1 if is_awarded_item else 0

            pl_no, drawing_no = self._get_po_item_identifiers(
                schedule_row.item,
                tender_item,
            )
            schedule_row.pl_no = pl_no or ""
            schedule_row.drawing_no = drawing_no or ""

            qty = flt(schedule_row.po_quantity)
            rate = flt(schedule_row.po_rate)
            schedule_row.po_total = qty * rate
            total += flt(schedule_row.po_total)

        self.po_amount_received = total

    @staticmethod
    def _get_awarded_quantity(tender_item):
        """Return the quantity that may be scheduled for an awarded item."""
        if not tender_item:
            return 0

        if flt(tender_item.awarded_quantity) > 0:
            return flt(tender_item.awarded_quantity)

        if (
            tender_item.outcome == "Partially Won"
            and flt(tender_item.award_share_percent) > 0
        ):
            return (
                flt(tender_item.quantity)
                * flt(tender_item.award_share_percent)
                / 100
            )

        if tender_item.outcome == "Won":
            return flt(tender_item.quantity)

        return 0

    @staticmethod
    def _get_po_item_identifiers(item_code, tender_item=None):
        """Return PL and Drawing numbers using stable source precedence.

        Source order:
        1. Item custom fields maintained by PEPL Product Master.
        2. PEPL Product Master itself.
        3. Values already captured on the Tender Item row.
        """
        if not item_code:
            return "", ""

        pl_no = ""
        drawing_no = ""

        item_fields = []
        if frappe.db.has_column("Item", "custom_pl_no"):
            item_fields.append("custom_pl_no")
        if frappe.db.has_column("Item", "custom_drawing_no"):
            item_fields.append("custom_drawing_no")

        if item_fields:
            item_values = frappe.db.get_value(
                "Item",
                item_code,
                item_fields,
                as_dict=True,
            ) or {}
            pl_no = item_values.get("custom_pl_no") or ""
            drawing_no = item_values.get("custom_drawing_no") or ""

        if not pl_no or not drawing_no:
            product = frappe.db.get_value(
                "PEPL Product Master",
                {"linked_item": item_code},
                ["pl_number", "drawing_number"],
                as_dict=True,
            ) or {}
            pl_no = pl_no or product.get("pl_number") or ""
            drawing_no = drawing_no or product.get("drawing_number") or ""

        if tender_item:
            pl_no = pl_no or getattr(tender_item, "pl_no", None) or ""
            drawing_no = (
                drawing_no
                or getattr(tender_item, "drawing_no", None)
                or ""
            )

        return pl_no, drawing_no



@frappe.whitelist()
def auto_populate_bid_documents(tender_name):
    """Auto-populate bid documents from customer-specific approvals."""
    tender = frappe.get_doc("PEPL Tender", tender_name)
    tender.check_permission("write")

    if tender.docstatus != 0:
        frappe.throw(
            _("The document checklist can be generated only before submission.")
        )

    if not tender.items:
        frappe.throw(
            _("Add Tender Items before generating the document checklist.")
        )
    if not tender.customer:
        frappe.throw(_("Customer must be set on the Tender."))
    if not tender.sector:
        frappe.throw(_("Sector must be set on the Tender."))

    from pepl_sales.pepl_sales.doctype.vendor_approval_status.vendor_approval_status import (
        get_approval_status_for_item,
    )

    all_required_docs = []
    approval_warnings = []

    for item_row in tender.items:
        approval = get_approval_status_for_item(
            tender.customer,
            item_row.item,
            tender.sector,
        )

        item_row.vendor_approval_record = approval.get("name")
        item_row.vendor_approval_stage = approval.get("stage") or "No Record"
        item_row.vendor_approval_health = approval.get("health") or "Missing"
        item_row.vendor_approval_expiry = approval.get("expiry_date")
        item_row.vendor_approval_warning = approval.get("warning") or ""

        all_required_docs.extend(
            approval.get("required_documents") or []
        )

        if approval.get("health") in {
            "Expired",
            "Expiring Soon",
            "Missing",
        }:
            approval_warnings.append(
                "{0}: {1}".format(
                    item_row.item,
                    approval.get("warning")
                    or approval.get("health"),
                )
            )

    all_required_docs = list(dict.fromkeys(all_required_docs))

    existing_doc_types = {
        row.document_type
        for row in tender.bid_documents or []
        if row.document_type
    }

    added = 0
    for document_type in all_required_docs:
        if document_type in existing_doc_types:
            continue

        tender.append(
            "bid_documents",
            {
                "document_source": "Auto-Required",
                "document_type": document_type,
                "is_mandatory": 1,
                "is_attached": 0,
            },
        )
        existing_doc_types.add(document_type)
        added += 1

    tender.save()

    return {
        "added": added,
        "total_required": len(all_required_docs),
        "approval_warnings": approval_warnings,
        "warning_count": len(approval_warnings),
    }


@frappe.whitelist()
def get_tender_summary(filters=None):
    """Return aggregated Tender pipeline summary."""
    return frappe.db.sql(
        """
        SELECT
            sector,
            status,
            COUNT(*) as count,
            SUM(total_estimated_value) as total_estimated,
            SUM(total_bid_value) as total_bid,
            SUM(items_won) as items_won_count
        FROM `tabPEPL Tender`
        GROUP BY sector, status
        ORDER BY sector, status
        """,
        as_dict=True,
    )


def _custom_field_exists_on_so(field_name):
    """Check whether a field column exists on Sales Order."""
    return frappe.db.has_column("Sales Order", field_name)


@frappe.whitelist()
def create_sales_order_from_tender(tender_name):
    """Create Sales Order from Tender PO Schedule."""
    tender = frappe.get_doc("PEPL Tender", tender_name)
    tender.check_permission("write")

    if not frappe.has_permission("Sales Order", "create"):
        frappe.throw(
            _("You do not have permission to create Sales Orders."),
            frappe.PermissionError,
        )

    if tender.docstatus not in {0, 1}:
        frappe.throw(_("A cancelled Tender cannot create a Sales Order."))

    if tender.status not in {"Won", "Partially Won"}:
        frappe.throw(
            _(
                "Tender must be Won or Partially Won. "
                "Current status: {0}"
            ).format(tender.status)
        )
    if not tender.customer_po_received:
        frappe.throw(
            _(
                "Customer PO/LOA must be received before creating "
                "the Sales Order."
            )
        )
    if not tender.po_number:
        frappe.throw(_("Customer PO Number is required."))
    if not tender.po_date:
        frappe.throw(_("Customer PO Date is required."))

    if getdate(tender.po_date) > getdate(today()):
        frappe.throw(
            _(
                "Customer PO Date {0} cannot be in the future."
            ).format(tender.po_date)
        )

    if tender.linked_sales_order:
        frappe.throw(
            _("Sales Order {0} is already linked.").format(
                tender.linked_sales_order
            )
        )
    if not tender.po_schedule:
        frappe.throw(_("PO Schedule is empty."))

    won_items = {
        row.item: row
        for row in tender.items or []
        if row.item and row.outcome in {"Won", "Partially Won"}
    }
    scheduled_quantities = {}

    for index, schedule_row in enumerate(
        tender.po_schedule,
        start=1,
    ):
        if not schedule_row.item:
            frappe.throw(_("Row {0}: Item is required.").format(index))
        if schedule_row.item not in won_items:
            frappe.throw(
                _(
                    "Row {0}: Item {1} is not marked Won or Partially Won "
                    "in the Tender Items table."
                ).format(index, schedule_row.item)
            )
        if flt(schedule_row.po_quantity) <= 0:
            frappe.throw(
                _("Row {0}: PO Quantity must be greater than zero.").format(
                    index
                )
            )
        if flt(schedule_row.po_rate) <= 0:
            frappe.throw(
                _("Row {0}: PO Rate must be greater than zero.").format(
                    index
                )
            )
        if not schedule_row.delivery_date:
            frappe.throw(
                _("Row {0}: Delivery Date is required.").format(index)
            )

        scheduled_quantities[schedule_row.item] = (
            flt(scheduled_quantities.get(schedule_row.item))
            + flt(schedule_row.po_quantity)
        )

    for item_code, scheduled_qty in scheduled_quantities.items():
        tender_item = won_items[item_code]
        allowed_qty = flt(tender_item.quantity)

        if tender_item.outcome == "Partially Won":
            if flt(tender_item.awarded_quantity) > 0:
                allowed_qty = flt(tender_item.awarded_quantity)
            elif flt(tender_item.award_share_percent) > 0:
                allowed_qty = (
                    flt(tender_item.quantity)
                    * flt(tender_item.award_share_percent)
                    / 100
                )

        if allowed_qty > 0 and scheduled_qty > allowed_qty:
            frappe.throw(
                _(
                    "PO Schedule quantity for item {0} is {1}, which exceeds "
                    "the awarded quantity {2}."
                ).format(item_code, scheduled_qty, allowed_qty)
            )

    earliest_delivery = min(
        (
            row.delivery_date
            for row in tender.po_schedule
            if row.delivery_date
        ),
        default=None,
    )

    sales_order = frappe.new_doc("Sales Order")
    sales_order.customer = tender.customer
    sales_order.po_no = tender.po_number
    sales_order.po_date = tender.po_date
    sales_order.delivery_date = (
        earliest_delivery or add_days(today(), 30)
    )
    sales_order.transaction_date = today()

    if tender.po_payment_terms:
        sales_order.payment_terms_template = tender.po_payment_terms

    if _custom_field_exists_on_so("custom_tender_reference"):
        sales_order.custom_tender_reference = tender.name
    if _custom_field_exists_on_so("custom_nit_number"):
        sales_order.custom_nit_number = tender.nit_number
    if _custom_field_exists_on_so("custom_sector"):
        sales_order.custom_sector = tender.sector

    for schedule_row in tender.po_schedule:
        sales_order.append(
            "items",
            {
                "item_code": schedule_row.item,
                "qty": schedule_row.po_quantity,
                "rate": schedule_row.po_rate,
                "delivery_date": schedule_row.delivery_date,
            },
        )

    sales_order.insert()

    if tender.docstatus == 0:
        tender.linked_sales_order = sales_order.name
        tender.status = "Order Received"
        tender.save()
    else:
        tender.db_set(
            "linked_sales_order",
            sales_order.name,
            update_modified=False,
        )
        tender.db_set(
            "status",
            "Order Received",
            update_modified=True,
        )

    return {
        "sales_order": sales_order.name,
        "url": f"/app/sales-order/{sales_order.name}",
        "lines_added": len(tender.po_schedule),
        "total_value": flt(tender.po_amount_received),
    }