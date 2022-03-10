"""
Functions to interact with database
"""
import dataclasses
import datetime

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa

from membank.handlers import GeneralMemoryError


# Mapping of Python types with SQL types
SQL_TABLE_TYPES = {
    float: sa.Float,
    str: sa.String,
    int: sa.Integer,
    datetime.datetime: sa.DateTime,
    datetime.date: sa.Date,
    bytes: sa.LargeBinary
}

def get_sql_col_type(py_type):
    """
    From Python data type py_type returns SQL type
    """
    if py_type in SQL_TABLE_TYPES:
        return SQL_TABLE_TYPES[py_type]
    raise GeneralMemoryError(f"Type {py_type} is not supported")

def make_stmt(sql_table, **filtering):
    """
    Prepares SQL statement and returns it
    """
    stmt = sa.select(sql_table)
    if filtering:
        for key, value in filtering.items():
            stmt = stmt.where(getattr(sql_table.c, key) == value)
    return stmt

def get_item(sql_table, engine, return_class, **filtering):
    """
    Get item from table
    """
    stmt = make_stmt(sql_table, **filtering)
    with engine.connect() as conn:
        cursor = conn.execute(stmt).first()
    return return_class(*cursor) if cursor else None

def get_all(sql_table, engine, return_class, **filtering):
    """
    Get all items from table
    """
    stmt = make_stmt(sql_table, **filtering)
    with engine.connect() as conn:
        cursor = conn.execute(stmt)
        return [return_class(*i) for i in cursor]

def update_item(sql_table, engine, item, key=None):
    """
    Creates or updates an item in table
    """
    stmt = sa.select(sql_table)
    if key:
        col = getattr(sql_table.c, key)
        val = getattr(item, key)
        stmt = stmt.where(col == val)
    else:
        for i in dataclasses.fields(item):
            col = getattr(sql_table.c, i.name)
            val = getattr(item, i.name)
            stmt = stmt.where(col == val)
    with engine.connect() as conn:
        rows = conn.execute(stmt)
        record = rows.first()
    if not record or (record and key):
        if record and key:
            col = getattr(sql_table.c, key)
            val = getattr(item, key)
            stmt = sql_table.update()
            stmt = stmt.where(col == val)
        else:
            stmt = sql_table.insert()
        stmt = stmt.values(dataclasses.asdict(item))
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(stmt)

def create_table(table, instance, engine):
    """
    Adds a memory attribute. Memory attribute must be instance of dataclass
    In database words this adds a new Table
    """
    with engine.connect() as conn:
        alembic = Operations(MigrationContext.configure(conn))
        fields = dataclasses.fields(instance)
        cols = []
        for field in fields:
            col_type = get_sql_col_type(field.type)
            col = sa.Column(field.name, col_type)
            cols.append(col)
        # pylint: disable=E1101
        try:
            alembic.create_table(table, *cols)
        except sa.exc.OperationalError as error:
            msg = error.args[0]
            if "table" in msg and "already exists" in msg:
                msg = f"Table {table} already exists. Use change instead"
                raise GeneralMemoryError(msg) from None
