import frappe

from pepl_sales.pepl_sales.tender_cst_sync import (
    backfill_existing_tender_cost_sheets,
)


def execute():
    result = backfill_existing_tender_cost_sheets(
        fail_fast=False
    )

    if result.get("failed"):
        frappe.log_error(
            message=frappe.as_json(
                result,
                indent=2,
            ),
            title=(
                "PEPL Tender CST Backfill "
                "- Review Required"
            ),
        )
