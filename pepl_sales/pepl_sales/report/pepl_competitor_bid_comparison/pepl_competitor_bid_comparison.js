frappe.query_reports["PEPL Competitor Bid Comparison"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("Outcome From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("Outcome To Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "tender",
            label: __("Tender"),
            fieldtype: "Link",
            options: "PEPL Tender"
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer"
        },
        {
            fieldname: "sector",
            label: __("Sector"),
            fieldtype: "Select",
            options: "\nRailways\nDefence\nPrivate\nOthers"
        },
        {
            fieldname: "item",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item"
        },
        {
            fieldname: "item_outcome",
            label: __("Item Outcome"),
            fieldtype: "Select",
            options: "\nPending\nWon\nPartially Won\nLost\nCancelled"
        },
        {
            fieldname: "competitor",
            label: __("Competitor Contains"),
            fieldtype: "Data"
        },
        {
            fieldname: "is_pepl",
            label: __("Bidder Type"),
            fieldtype: "Select",
            options: "\n1\n0",
            description: __("1 = PEPL only; 0 = competitors only")
        },
        {
            fieldname: "rank",
            label: __("Rank"),
            fieldtype: "Data",
            description: __("Examples: L1, L2, L10")
        },
        {
            fieldname: "winner_only",
            label: __("Winner Only"),
            fieldtype: "Check"
        }
    ]
};
