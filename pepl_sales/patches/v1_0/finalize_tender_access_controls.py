"""
Compatibility shim for a retired historical PEPL Tender migration.

The original patch modified Role Profiles and User assignments.
Those migration-time changes were intentionally removed from PEPL Sales
by commit 4387550 ("Remove Role Profile changes from migration").

This no-op module exists only so sites with the historical patch still
pending can complete migration safely without recreating the retired
Role Profile behavior.
"""


def execute():
    return
