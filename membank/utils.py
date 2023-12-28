"""Membank package wide utils."""
import dataclasses as data

from membank import errors as e


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
        msg = f"Item {instance} must be instance of dataclass"
        raise e.GeneralMemoryError(msg)
    for field in data.fields(instance):
        field_val = getattr(instance, field.name)
        if not isinstance(field_val, field.type):
            if field.type == float and isinstance(field_val, int):
                continue
            msg = f"Field '{field.name}' is not of type {field.type}"
            raise e.GeneralMemoryError(msg)
    return get_table_name(instance)


def get_table_name(cls):
    """Get table name."""
    table = getattr(cls, "__class__", False)
    if not table:
        return ""
    table = getattr(table, "__name__", "")
    return table.lower()
