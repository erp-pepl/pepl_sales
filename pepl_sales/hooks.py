app_name = "pepl_sales"
app_title = "PEPL Sales"
app_publisher = "Anshiv"
app_description = "Sales to Cash"
app_email = "erp.pepl@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

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
# after_install = "pepl_sales.install.after_install"

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

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"pepl_sales.tasks.all"
# 	],
# 	"daily": [
# 		"pepl_sales.tasks.daily"
# 	],
# 	"hourly": [
# 		"pepl_sales.tasks.hourly"
# 	],
# 	"weekly": [
# 		"pepl_sales.tasks.weekly"
# 	],
# 	"monthly": [
# 		"pepl_sales.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "pepl_sales.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "pepl_sales.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "pepl_sales.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["pepl_sales.utils.before_request"]
# after_request = ["pepl_sales.utils.after_request"]

# Job Events
# ----------
# before_job = ["pepl_sales.utils.before_job"]
# after_job = ["pepl_sales.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"pepl_sales.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

doc_events = {
    "Sales Order": {
        "on_submit": [
            "pepl_sales.pepl_sales.doctype.pepl_psd_tracker.pepl_psd_tracker.create_psd_tracker_for_so",
            "pepl_sales.pepl_sales.doctype.pepl_document_tracker.pepl_document_tracker.create_doc_tracker_for_so"
        ]
    },
    "Sales Invoice": {
        "on_submit": "pepl_sales.pepl_sales.doctype.pepl_payment_tracker.pepl_payment_tracker.create_payment_tracker_for_invoice"
    }
}

scheduler_events = {
    "daily": [
        "pepl_sales.pepl_sales.api.payment_tracker_jobs.update_all_payment_trackers_daily"
    ]
}
