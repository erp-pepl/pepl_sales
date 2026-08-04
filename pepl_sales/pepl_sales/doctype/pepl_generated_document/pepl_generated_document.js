frappe.ui.form.on(
    "PEPL Generated Document",
    {
        refresh(frm) {
            if (frm.is_new()) {
                return;
            }

            if (
                frm.doc.status !== "Issued"
                && frm.doc.template
            ) {
                frm.add_custom_button(
                    __("Generate PDF"),
                    () => generate_pdf(frm),
                    __("Actions")
                );
            }

            frm.add_custom_button(
                __("Create Revision"),
                () => create_revision(frm),
                __("Actions")
            );

            if (frm.doc.generated_file) {
                frm.add_custom_button(
                    __("Open Generated File"),
                    () => {
                        window.open(
                            frm.doc.generated_file,
                            "_blank"
                        );
                    },
                    __("Actions")
                );
            }
        }
    }
);


function generate_pdf(frm) {
    frappe.call({
        method: (
            "pepl_sales.pepl_sales.api."
            + "standard_document_generation."
            + "generate_pdf"
        ),
        args: {
            generated_document_name:
                frm.doc.name
        },
        freeze: true,
        freeze_message: __(
            "Generating controlled PDF..."
        ),
        callback(response) {
            const result =
                response.message || {};

            if (!result.generated_file) {
                frappe.msgprint(
                    __(
                        "The PDF could not be generated."
                    )
                );
                return;
            }

            frappe.show_alert({
                message: __(
                    "PDF generated successfully."
                ),
                indicator: "green"
            });

            frm.reload_doc();
        }
    });
}


function create_revision(frm) {
    frappe.confirm(
        __(
            "Create a new revision from "
            + "this document?"
        ),
        () => {
            frappe.call({
                method: (
                    "pepl_sales.pepl_sales.api."
                    + "standard_document_generation."
                    + "create_revision"
                ),
                args: {
                    generated_document_name:
                        frm.doc.name
                },
                freeze: true,
                freeze_message: __(
                    "Creating revision..."
                ),
                callback(response) {
                    const result =
                        response.message || {};

                    if (
                        !result.generated_document
                    ) {
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
    );
}
