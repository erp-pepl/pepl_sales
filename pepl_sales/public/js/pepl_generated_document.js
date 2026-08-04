frappe.ui.form.on(
    "PEPL Generated Document",
    {
        refresh(frm) {
            if (frm.is_new()) {
                return;
            }

            if (
                frm.doc.template
                && frm.doc.status !== "Issued"
            ) {
                frm.add_custom_button(
                    __("Generate PDF"),
                    function () {
                        pepl_generate_pdf(frm);
                    },
                    __("Actions")
                );
            }

            frm.add_custom_button(
                __("Create Revision"),
                function () {
                    pepl_create_revision(frm);
                },
                __("Actions")
            );

            if (frm.doc.generated_file) {
                frm.add_custom_button(
                    __("Open Generated File"),
                    function () {
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


function pepl_generate_pdf(frm) {
    if (!frm.doc.template) {
        frappe.msgprint(
            __("Select a Template first.")
        );
        return;
    }

    if (frm.doc.status === "Issued") {
        frappe.msgprint(
            __(
                "Issued documents cannot be regenerated. "
                + "Create a new revision instead."
            )
        );
        return;
    }

    frappe.call({
        method: [
            "pepl_sales",
            "pepl_sales",
            "doctype",
            "pepl_generated_document",
            "pepl_generated_document",
            "generate_pdf"
        ].join("."),

        args: {
            docname: frm.doc.name
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
                        "The PDF could not be generated. "
                        + "Review the Error Log field."
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


function pepl_create_revision(frm) {
    frappe.confirm(
        __(
            "Create a new controlled revision "
            + "from this document?"
        ),
        function () {
            frappe.call({
                method: [
                    "pepl_sales",
                    "pepl_sales",
                    "doctype",
                    "pepl_generated_document",
                    "pepl_generated_document",
                    "create_revision"
                ].join("."),

                args: {
                    docname: frm.doc.name
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
                        frappe.msgprint(
                            __(
                                "The revision could "
                                + "not be created."
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
    );
}
