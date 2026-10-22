### PEPL Sales

Sales to Cash

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app pepl_sales
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/pepl_sales
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### List View hover preview (every DocType)

Rest the mouse on any row of any List View for half a second: a card shows that record (status strip,
number and status, main fields, the amount, the item table with a Total row and, on submitted documents,
GL Entries / Stock Movement). ERPNext permissions apply.

- Browser: `pepl_sales/public/js/pepl_list_hover.bundle.js` and `public/css/pepl_list_hover.bundle.css`
- Server and per-DocType layout: `pepl_sales/list_preview.py` (`PREVIEW_CONFIG`); DocTypes not listed get an automatic card
- Tests: `pepl_sales/tests/test_list_preview.py`


### License

mit
