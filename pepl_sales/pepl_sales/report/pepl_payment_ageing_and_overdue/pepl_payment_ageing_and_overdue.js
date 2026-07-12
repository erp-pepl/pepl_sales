frappe.query_reports["PEPL Payment Ageing and Overdue"] = {
    filters: [
        {
            fieldname: "payment_tracker",
            label: __("Payment Tracker"),
            fieldtype: "Link",
            options: "PEPL Payment Tracker"
        },
        {
            fieldname: "sales_invoice",
            label: __("Sales Invoice"),
            fieldtype: "Link",
            options: "Sales Invoice"
        },
        {
            fieldname: "sales_order",
            label: __("Sales Order"),
            fieldtype: "Link",
            options: "Sales Order"
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
            fieldname: "payment_status",
            label: __("Payment Status"),
            fieldtype: "Select",
            options: [
                "",
                "Pending Dispatch",
                "Dispatched",
                "R-Note Received",
                "I-Note Received",
                "JCC Issued",
                "Bills Submitted",
                "CO7 Issued",
                "Payment Received",
                "Reconciled",
                "Closed"
            ].join("\n")
        },
        {
            fieldname: "ageing_bucket",
            label: __("Ageing Bucket"),
            fieldtype: "Select",
            options: [
                "",
                "0-30 days",
                "31-45 days",
                "45+ days (MSME breach)"
            ].join("\n")
        },
        {
            fieldname: "outstanding_only",
            label: __("Outstanding Only"),
            fieldtype: "Check",
            default: 1
        },
        {
            fieldname: "overdue_only",
            label: __("Overdue Only"),
            fieldtype: "Check"
        },
        {
            fieldname: "msme_breach_only",
            label: __("MSME Breach Only"),
            fieldtype: "Check"
        },
        {
            fieldname: "minimum_days_overdue",
            label: __("Minimum Days Overdue"),
            fieldtype: "Int",
            default: 0
        }
    ]
};
