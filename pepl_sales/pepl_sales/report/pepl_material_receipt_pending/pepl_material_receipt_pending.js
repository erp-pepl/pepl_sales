frappe.query_reports["PEPL Material Receipt Pending"] = {
    filters: [
        {
            fieldname: "document_tracker",
            label: __("Document Tracker"),
            fieldtype: "Link",
            options: "PEPL Document Tracker"
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
            fieldname: "receipt_status",
            label: __("Receipt Status"),
            fieldtype: "Select",
            options: "\nPending\nReceived\nFiled\nObsolete"
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
            fieldname: "pending_only",
            label: __("Pending Only"),
            fieldtype: "Check",
            default: 1
        },
        {
            fieldname: "minimum_pending_days",
            label: __("Minimum Pending Days"),
            fieldtype: "Int",
            default: 0
        }
    ]
};
