app_name = "pepl_sales"
app_title = "PEPL Sales"
app_publisher = "Anshiv"
app_description = "Sales to Cash"
app_email = "erp.pepl@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "pepl_sales",
# 		"logo": "/assets/pepl_sales/logo.png",
# 		"title": "PEPL Sales",
# 		"route": "/pepl_sales",
# 		"has_permission": "pepl_sales.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/pepl_sales/css/pepl_sales.css"
# app_include_js = "/assets/pepl_sales/js/pepl_sales.js"

# include js, css files in header of web template
# web_include_css = "/assets/pepl_sales/css/pepl_sales.css"
# web_include_js = "/assets/pepl_sales/js/pepl_sales.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "pepl_sales/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}

doctype_js = {
    "Sales Order": "public/js/sales_order.js",
    "Sales Invoice": "public/js/sales_invoice.js",
    "PEPL Payment Tracker":
        "public/js/pepl_payment_tracker.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "pepl_sales/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "pepl_sales.utils.jinja_methods",
# 	"filters": "pepl_sales.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "pepl_sales.install.before_install"
after_install = "pepl_sales.install.after_install"
before_migrate = "pepl_sales.setup.mom_phase1.before_migrate"
after_migrate = "pepl_sales.setup.mom_phase1.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "pepl_sales.uninstall.before_uninstall"
# after_uninstall = "pepl_sales.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "pepl_sales.utils.before_app_install"
# after_app_install = "pepl_sales.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "pepl_sales.utils.before_app_uninstall"
# after_app_uninstall = "pepl_sales.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "pepl_sales.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Sales Order": {
        "validate": "pepl_sales.events.validate_sales_order_sector",
        "on_submit": "pepl_sales.events.on_sales_order_submit",
    },

    "Sales Invoice": {
        "before_submit": (
            "pepl_sales.overrides.sales_invoice."
            "validate_document_readiness_before_submit"
        ),
        "on_submit": "pepl_sales.events.on_sales_invoice_submit",
    },

    "PEPL Document Tracker": {
        "validate": (
            "pepl_sales.document_tracker_validation."
            "validate_document_tracker"
        ),
    },

    "PEPL Payment Tracker": {
        "validate": (
            "pepl_sales.payment_tracker_validation."
            "validate_payment_tracker"
        ),
    },

    "PEPL CST Cost Sheet": {
        "on_trash": (
            "pepl_sales.pepl_sales.tender_cst_sync."
            "clear_cst_from_tender"
        ),
    },

    "Payment Entry": {
        "on_submit": "pepl_sales.events.on_payment_entry_submit",
        "on_update_after_submit": (
            "pepl_sales.events."
            "on_payment_entry_update_after_submit"
        ),
        "on_cancel": "pepl_sales.events.on_payment_entry_cancel",
    },
}

scheduler_events = {'daily': ['pepl_sales.pepl_sales.api.payment_tracker_jobs.update_all_payment_trackers_daily', 'pepl_sales.operational_notifications.run_daily_operational_notifications']}

# PEPL Generated Document explicit client script
try:
    doctype_js
except NameError:
    doctype_js = {}

doctype_js.update({
    "PEPL Generated Document":
        "public/js/pepl_generated_document.js",
})

# PEPL PSD Tracker business validation
try:
    doc_events
except NameError:
    doc_events = {}

_existing_psd_tracker_events = (
    doc_events.get("PEPL PSD Tracker")
    or {}
)

_existing_psd_tracker_events["validate"] = (
    "pepl_sales.pepl_sales.validations."
    "psd_tracker.validate_psd_tracker"
)

doc_events["PEPL PSD Tracker"] = (
    _existing_psd_tracker_events
)

# PEPL PSD Tracker explicit client script
try:
    doctype_js
except NameError:
    doctype_js = {}

doctype_js.update({
    "PEPL PSD Tracker":
        "public/js/pepl_psd_tracker.js",
})

