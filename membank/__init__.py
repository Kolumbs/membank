"""
Defines interfaces exposed to library user.

>>> from dataclasses import dataclass, field
>>> from membank import LoadMemory
>>> memory = LoadMemory()
>>> @dataclass
... class User:
...     id: int = field(metadata={"key": True})
...     name: str
>>> memory.put(User(id=1, name="Alice"))
"""

from membank.errors import (GeneralMemoryError, MemoryFilteringError,
                            MemoryOutOfSyncError, MemoryTableDoesNotExist)
from membank.interface import LoadMemory

__all__ = [
    "LoadMemory",
    "GeneralMemoryError",
    "MemoryTableDoesNotExist",
    "MemoryFilteringError",
    "MemoryOutOfSyncError",
]
