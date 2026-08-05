frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        pepl_add_sales_invoice_document_button(
            frm
        );
    }
});


function pepl_add_sales_invoice_document_button(
    frm
) {
    if (
        frm.is_new()
        || frm.doc.docstatus !== 1
    ) {
        return;
    }

    frm.add_custom_button(
        __("Generate Standard Document"),
        () => {
            pepl_open_sales_invoice_document_dialog(
                frm
            );
        },
        __("PEPL")
    );
}


function pepl_open_sales_invoice_document_dialog(
    frm
) {
    const allowed_requirements = [
        "GST_SUMMARY",
        "GUARANTEE_CERTIFICATE",
        "CONTRACTOR_BILL"
    ];

    const sector = (
        frm.doc.custom_sector
        || frm.doc.sector
        || "Common"
    );

    const dialog = new frappe.ui.Dialog({
        title: __(
            "Generate Sales Invoice Document"
        ),
        fields: [
            {
                fieldname: "template_name",
                fieldtype: "Link",
                options:
                    "PEPL Standard Document Template",
                label:
                    __("Document Template"),
                reqd: 1,
                get_query() {
                    return {
                        filters: {
                            active: 1,
                            status: "Approved",
                            document_requirement: [
                                "in",
                                allowed_requirements
                            ],
                            sector: [
                                "in",
                                [
                                    "Common",
                                    sector
                                ]
                            ]
                        }
                    };
                }
            }
        ],
        primary_action_label:
            __("Create Document"),
        primary_action(values) {
            dialog.hide();

            frappe.call({
                method:
                    "pepl_sales.pepl_sales.api."
                    + "standard_document_generation."
                    + "create_from_business_source",
                args: {
                    source_doctype:
                        "Sales Invoice",
                    source_document:
                        frm.doc.name,
                    template_name:
                        values.template_name
                },
                freeze: true,
                freeze_message:
                    __(
                        "Creating controlled "
                        + "document..."
                    ),
                callback(response) {
                    const result = (
                        response.message
                        || {}
                    );

                    if (
                        !result.generated_document
                    ) {
                        frappe.msgprint(
                            __(
                                "Generated Document "
                                + "was not created."
                            )
                        );
                        return;
                    }

                    frappe.set_route(
                        "Form",
                        "PEPL Generated Document",
                        result.generated_document
                    );
                }
            });
        }
    });

    dialog.show();
}
