"""
Compatibility patch for historical PEPL Tender access-control migration.

The original implementation modified Role Profiles and User assignments.
Those migration-time Role Profile changes were intentionally retired by
commit 4387550 ("Remove Role Profile changes from migration").

Some existing sites may still have this historical patch pending in their
migration state. Keeping this module as a no-op allows those sites to finish
migration safely without recreating the retired Role Profile mutations.
"""


def execute():
    """Complete the retired historical migration without changing data."""
    return
