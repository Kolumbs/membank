"""Exceptions for membank."""


class GeneralMemoryError(Exception):
    """All general errors in memory interface."""


class MemoryFilteringError(Exception):
    """Error with filtering different tables at the same time."""

    def __init__(self, table1, table2):
        """Initialise message."""
        msg = f"Not possible to filter {table1} and {table2}"
        msg += " at the same time"
        Exception.__init__(self, msg)


class MemoryOutOfSyncError(Exception):
    """Error when memory is out of sync with database."""

    def __init__(self, table_name, name):
        """Initialise message."""
        msg = f"Object '{table_name}' appears to be out of sync"
        msg += f" as '{name}' is not found"
        Exception.__init__(self, msg)
