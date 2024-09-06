"""Module supports dataclass storage and retrieval."""

from dataclasses import dataclass
import pickle

from membank import errors as e
from membank.datamethods import create_table, get_item, update_item


@dataclass
class TableClass:
    """Maps a dataclass to a Table."""

    table: str = ""
    classload: bytes = b""


class Mapper:
    """Interface to store and retrieve dataclasses."""

    def __init__(self, engine, metadata):
        """Initialise."""
        self.engine = engine
        self.metadata = metadata
        if "__meta_dataclasses__" not in metadata:
            self._create_meta()
        self.sql_table = self.metadata.tables["__meta_dataclasses__"]

    def _create_meta(self):
        """Create __meta_dataclasses__ table."""
        create_table("__meta_dataclasses__", TableClass(), self.engine)
        self.metadata.reflect(bind=self.engine)

    def _handle_missing_meta(self, func, *args, **kwargs):
        """Run function such that missing __meta_dataclasses are taken into account.

        Upon exception that table __meta_dataclasses__ is missing, fix it and reraise,
        otherwise just raises error.
        """
        try:
            return func(*args, **kwargs)
        except e.MemoryTableDoesNotExist:
            self._create_meta()
            raise

    def get_class(self, table):
        """Return dataclass representing table."""
        try:
            table_class = self._handle_missing_meta(
                get_item, self.sql_table, self.engine, TableClass, **{"table": table}
            )
        except e.MemoryTableDoesNotExist:
            table_class = None
        if table_class:
            return pickle.loads(table_class.classload)
        return None

    def put_class(self, table, table_class):
        """Store dataclass representing table."""
        classload = pickle.dumps(table_class)
        args = (
            self.sql_table,
            self.engine,
            TableClass(table=table, classload=classload),
        )
        kargs = {"key": "table"}
        try:
            self._handle_missing_meta(update_item, *args, **kargs)
        except e.MemoryTableDoesNotExist:
            update_item(*args, **kargs)
