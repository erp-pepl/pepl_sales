frappe.query_reports["PEPL Sales Invoice Document Status"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer"
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
            fieldname: "sector",
            label: __("Sector"),
            fieldtype: "Select",
            options: [
                "",
                "Railways",
                "Defence",
                "Private",
                "Others"
            ].join("\n")
        },
        {
            fieldname: "overall_status",
            label: __("Overall Document Status"),
            fieldtype: "Select",
            options: [
                "",
                "Pending",
                "Complete",
                "Tracker Missing",
                "No Sales Order"
            ].join("\n")
        }
    ]
};
