frappe.query_reports["PEPL Customer Sales-to-Cash Status"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("SO From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("SO To Date"),
            fieldtype: "Date"
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
            fieldname: "sales_order_status",
            label: __("Sales Order Status"),
            fieldtype: "Data"
        },
        {
            fieldname: "cycle_status",
            label: __("Cycle Status"),
            fieldtype: "Select",
            options: [
                "",
                "Sales Order Created",
                "Order Execution",
                "Invoice Raised",
                "Payment Pending",
                "Payment Complete"
            ].join("\n")
        },
        {
            fieldname: "missing_only",
            label: __("Missing Stages Only"),
            fieldtype: "Check"
        },
        {
            fieldname: "outstanding_only",
            label: __("Outstanding Only"),
            fieldtype: "Check"
        }
    ]
};
