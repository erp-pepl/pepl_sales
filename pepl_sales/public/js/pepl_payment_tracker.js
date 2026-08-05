frappe.ui.form.on("PEPL Payment Tracker", {
    refresh(frm) {
        pepl_add_payment_request_button(
            frm
        );
    }
});


function pepl_add_payment_request_button(frm) {
    if (frm.is_new()) {
        return;
    }

    if (!frm.doc.linked_sales_invoice) {
        return;
    }

    frm.add_custom_button(
        __("Generate Payment Request"),
        () => {
            pepl_open_payment_request_dialog(
                frm
            );
        },
        __("PEPL")
    );
}


function pepl_open_payment_request_dialog(
    frm
) {
    const dialog = new frappe.ui.Dialog({
        title: __("Generate Payment Request"),
        fields: [
            {
                fieldname: "template_name",
                fieldtype: "Link",
                options:
                    "PEPL Standard Document Template",
                label:
                    __("Document Template"),
                reqd: 1,
                default:
                    "TPL_PAYMENT_REQUEST",
                get_query() {
                    return {
                        filters: {
                            active: 1,
                            status: "Approved",
                            document_requirement:
                                "PAYMENT_REQUEST",
                            sector: [
                                "in",
                                [
                                    "Common",
                                    frm.doc.sector
                                        || "Common"
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
                        "PEPL Payment Tracker",
                    source_document:
                        frm.doc.name,
                    template_name:
                        values.template_name
                },
                freeze: true,
                freeze_message:
                    __(
                        "Creating controlled "
                        + "payment request..."
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
