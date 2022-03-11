"""
Exceptions for membank
"""


class GeneralMemoryError(Exception):
    """
    All general errors in memory interface
    """

class MemoryFilteringError(Exception):
    """
    Error with filtering different tables at the same time
    """

    def __init__(self, table1, table2):
        msg = f"Not possible to filter {table1} and {table2}"
        msg += " at the same time"
        Exception.__init__(self, msg)
