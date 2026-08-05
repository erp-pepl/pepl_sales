frappe.ui.form.on(
    "PEPL PSD Tracker",
    {
        refresh(frm) {
            if (frm.is_new()) {
                return;
            }

            frm.add_custom_button(
                __("Generate Standard Document"),
                function () {
                    open_generation_dialog(frm);
                },
                __("Actions")
            );
        }
    }
);


function open_generation_dialog(frm) {
    const entries = (
        frm.doc.psd_entries || []
    );

    if (!entries.length) {
        frappe.msgprint(
            __("No PSD Entries are available.")
        );
        return;
    }

    const entry_options = entries.map(
        function (row) {
            const label = [
                row.entry_label || row.name,
                row.security_mode || "",
                row.bg_number || ""
            ].filter(Boolean).join(" — ");

            return {
                label: label,
                value: row.name
            };
        }
    );

    const dialog = new frappe.ui.Dialog({
        title: __(
            "Generate Standard Document"
        ),
        fields: [
            {
                fieldname: "psd_entry_row",
                label: __("PSD Entry"),
                fieldtype: "Select",
                options: entry_options,
                reqd: 1
            },
            {
                fieldname: "template_name",
                label: __("Document Template"),
                fieldtype: "Link",
                options:
                    "PEPL Standard Document Template",
                reqd: 1,
                get_query() {
                    return {
                        filters: {
                            active: 1,
                            status: "Approved"
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
                method: [
                    "pepl_sales",
                    "pepl_sales",
                    "api",
                    "standard_document_generation",
                    "create_from_psd_tracker"
                ].join("."),
                args: {
                    tracker_name:
                        frm.doc.name,
                    template_name:
                        values.template_name,
                    psd_entry_row:
                        values.psd_entry_row
                },
                freeze: true,
                freeze_message: __(
                    "Creating controlled document..."
                ),
                callback(response) {
                    const result =
                        response.message || {};

                    if (
                        result.generated_document
                    ) {
                        frappe.set_route(
                            "Form",
                            "PEPL Generated Document",
                            result.generated_document
                        );
                    }
                }
            });
        }
    });

    dialog.show();
}
