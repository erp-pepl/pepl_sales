frappe.query_reports["PEPL Tender Win Loss Analysis"] = {
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
            fieldname: "status",
            label: __("Tender Status"),
            fieldtype: "Select",
            options: [
                "",
                "Draft",
                "Active Bid",
                "Costing",
                "Costed",
                "Submitted",
                "Won",
                "Partially Won",
                "Order Received",
                "Lost",
                "No Bid",
                "Cancelled",
                "Re-tendered"
            ].join("\n")
        },
        {
            fieldname: "item",
            label: __("Item"),
            fieldtype: "Link",
            options: "Item"
        },
        {
            fieldname: "loss_reason",
            label: __("Loss Category"),
            fieldtype: "Select",
            options: [
                "",
                "Price",
                "Technical Non-Compliance",
                "Delivery Schedule",
                "Vendor Approval / Eligibility",
                "Commercial Terms",
                "Documentation",
                "Customer Preference",
                "Competitor Relationship",
                "Purchase Preference / Policy",
                "Tender Cancelled",
                "No Bid / Withdrawn",
                "Other"
            ].join("\n")
        },
        {
            fieldname: "competitor",
            label: __("Competitor Contains"),
            fieldtype: "Data"
        }
    ]
};
