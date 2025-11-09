"""Module supports dataclass storage and retrieval."""

import dataclasses as data
import pickle

from membank import errors as e
from membank.datamethods import (create_table, get_item,
                                 introspect_table_fields, update_item)


def is_fallback_class(cls):
    """Check if class is a fallback class."""
    if not isinstance(cls, type):
        raise TypeError(f"{cls} must be a class type")
    name = getattr(cls, "__name__", "")
    return name.startswith("__") and name.endswith("Fallback__")


def is_reserved_table_name(table):
    """Check if table name is reserved by membank."""
    reserved_names = [
        "__meta_dataclasses__",
    ]
    if table in reserved_names or table.startswith("__") and table.endswith("fallback__"):
        return True
    return False


def assert_table_name(instance):
    """Verify that instance is a dataclass instance.

    Verify also that instance has all fields as per annotated types.
    Return valid table name from instance.
    Raise e.GeneralMemoryError otherwise.
    """
    if isinstance(instance, type):
        msg = f"Item {instance} is a class but must be instance of class"
        raise e.GeneralMemoryError(msg)
    if not data.is_dataclass(instance):
        msg = f"Item {instance} must be instance of dataclass was {type(instance)}"
        raise e.GeneralMemoryError(msg)
    for field in data.fields(instance):
        field_val = getattr(instance, field.name)
        if not isinstance(field_val, field.type):
            if field.type == float and isinstance(field_val, int):
                continue
            msg = "{instance}: has field '{field.name}' of type {type(field_val)} "
            msg += "but must be of type {field.type}"
            raise e.GeneralMemoryError(msg)
    return get_table_name(instance)


def get_table_name(cls):
    """Get table name."""
    table = getattr(cls, "__class__", False)
    if not table:
        return ""
    return get_class_name(table)


def get_class_name(cls):
    """Get class name."""
    name = getattr(cls, "__name__", "")
    if is_fallback_class(cls):
        name = name[2:-10]
    return name.lower()


@data.dataclass
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

    def _get_temporary_fallback_class(self, table):
        """Return a temporary fallback dataclass for given table."""
        self.metadata.reflect(bind=self.engine)
        cls_name = "__" + table.capitalize() + "Fallback__"
        fields = introspect_table_fields(self.metadata.tables[table])
        return data.make_dataclass(cls_name, fields)

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
        return self._get_temporary_fallback_class(table)

    def put_class(self, table, table_class):
        """Store dataclass representing table."""
        if table_class.__name__.endswith("Fallback__"):
            return
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
