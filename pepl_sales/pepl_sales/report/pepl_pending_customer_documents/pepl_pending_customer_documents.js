frappe.query_reports["PEPL Pending Customer Documents"] = {
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
            fieldname: "document_type",
            label: __("Document Type"),
            fieldtype: "Select",
            options: [
                "",
                "Customer PO",
                "Material Receipt",
                "Customer Receipt",
                "R-Note",
                "I-Note",
                "CO7",
                "JCC",
                "Bill Submission",
                "Payment Advice",
                "NDA",
                "Others"
            ].join("\n")
        },
        {
            fieldname: "document_status",
            label: __("Document Status"),
            fieldtype: "Select",
            options: "\nPending\nReceived\nSent\nFiled\nObsolete",
            description: __(
                "Leave blank to show all statuses except Received and Filed."
            )
        },
        {
            fieldname: "direction",
            label: __("Direction"),
            fieldtype: "Select",
            options: [
                "",
                "Inbound (from Customer)",
                "Outbound (to Customer)",
                "Internal",
                "From Bank",
                "To Bank"
            ].join("\n")
        },
        {
            fieldname: "required_only",
            label: __("Required Only"),
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
