"""
Defines interface class and functions for library
"""
import datetime
import os
import typing
import urllib.parse

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


# Mapping of Python types with SQL types
SQL_TABLE_TYPES = {
    float: sa.Float,
    str: sa.String,
    int: sa.Integer,
    datetime.datetime: sa.DateTime,
}

def get_sql_col_type(py_type):
    """
    From Python data type py_type returns SQL type
    """
    if py_type in SQL_TABLE_TYPES:
        return SQL_TABLE_TYPES[py_type]
    raise GeneralMemoryError(f"Type {py_type} is not supported")


class GeneralMemoryError(Exception):
    """
    All general errors in memory interface
    """


# pylint: disable=R0903
class Attributer():
    """
    Wraps handling attribute calls for get
    """

    def __init__(self, table, engine, metadata):
        self.__engine = engine
        self.__metadata = metadata
        self.name = table
        self.__table = None

    def __call__(self, **kargs):
        if self.name not in self.__metadata.tables:
            raise GeneralMemoryError(f"{self.name} is not found in memory")
        self.__table = self.__metadata.tables[self.name]
        return self.__get_call(**kargs)

    def __get_call(self, **filtering):
        """
        Get item from SQL table
        """
        stmt = sa.select(self.__table)
        if filtering:
            for key, value in filtering.items():
                stmt = stmt.where(getattr(self.__table.c, key) == value)
        with self.__engine.connect() as conn:
            cursor = conn.execute(stmt).all()
        item = cursor[0] if cursor else None
        class_result = type(self.name.capitalize(), (typing.NamedTuple,), item._asdict())
        return class_result()


class MemoryBlob():
    """
    Allows to access generically put method attributes
    """

    def __init__(self, engine, metadata):
        """
        Initialises attribute/table list
        """
        self.__attrs = {}
        self.__engine = engine
        self.__metadata = metadata

    def __getattr__(self, name):
        if name in self.__attrs:
            return self.__attrs[name]
        new_attr = Attributer(name, self.__engine, self.__metadata)
        self.__attrs[name] = new_attr
        return new_attr


def assert_path(path, db_type):
    """
    Checks for valid path, raises GeneralError if any issue
    """
    msg = None
    if ":memory:" == path:
        if db_type != "sqlite":
            msg = f"Path '{path}' is only allowed to sqlite database"
    else:
        path_dir = os.path.dirname(path)
        path_dir = path_dir if path_dir else "."
        if not os.path.isdir(path_dir):
            msg = f"Directory '{path_dir}' does not exist"
        elif not os.access(path_dir, os.W_OK):
            msg = f"Directory '{path_dir}' is missing write permissions"
    if msg:
        raise GeneralMemoryError(msg)


class LoadMemory():
    """
    Loads memory and provides methods to create, change and access it
    """

    def __init__(self, url=False, debug=False):
        """
        debug - more verbose logging
        url - resource locator according to RFC-1738 with scheme to designate database type
        to be used, e.g. sqlite, postgresql, berkeleydb and scheme specific part always follow
        either Common Internet Scheme Syntax or using File scheme part
        Special note on relative vs. absolute file path handling
        As RFC-1738 does not allow relative file paths, special notation is used only for
        local file based access databases e.g. sqlite, berkeleydb. To make relative path,
        host location of file path must be used i.e. file://{relative_path}. For absolute
        paths host part must be empty i.e. file:///{abosulute_path}
        """
        if not url:
            url = "sqlite://:memory:"
        url = urllib.parse.urlparse(url)
        if url.scheme in ["sqlite"]:
            path = url.netloc + url.path
            assert_path(path, url.scheme)
            url = sa.engine.URL.create(
                drivername = url.scheme,
                database = path,
            )
            self.__engine = sa.create_engine(
                url,
                echo = debug,
                future = True,
            )
            self.__metadata = sa.MetaData()
        else:
            raise GeneralMemoryError(f"Such database type {url.scheme} is not supported")
        self.__load_attributes()

    def __load_attributes(self):
        """
        Loads all memory attributes
        """
        self.__metadata.reflect(bind=self.__engine)
        self.get = MemoryBlob(self.__engine, self.__metadata)

    def __create_table(self, table, mem):
        """
        Adds a memory attribute. Memory attribute must resemble namedtuple
        In database words this adds a new Table
        If 'id' is not given in attributes, it is automatically added as a reference
        to be able to get back specific memory item
        """
        with self.__engine.connect() as conn:
            alembic = Operations(MigrationContext.configure(conn))
            try:
                annotations = getattr(mem, "__annotations__")
                fields = list(mem._fields)
            except AttributeError:
                msg = "Creating new table requires annotated namedtuple. "
                msg += f"Instead got {mem}"
                raise GeneralMemoryError(msg) from AttributeError
            for i in [i for i in dir(mem) if i.startswith("add_")]:
                if not i[4:] in fields:
                    msg = f"Field {i[4:]} is not defined to be used in function {i}"
                    raise GeneralMemoryError(msg)
            cols = []
            for name in fields:
                col_type = annotations[name]
                col_type = get_sql_col_type(col_type)
                col = sa.Column(name, col_type)
                cols.append(col)
            if "id" not in fields:
                cols.append(sa.Column("id", sa.Integer))
            cols.append(sa.PrimaryKeyConstraint('id'))
            cols.append(sa.Index("idx_id", "id"))
            # pylint: disable=E1101
            try:
                alembic.create_table(table, *cols)
            except sa.exc.OperationalError as error:
                msg = error.args[0]
                if "table" in msg and "already exists" in msg:
                    msg = f"Table {table} already exists. Use change instead"
                    raise GeneralMemoryError(msg) from None
        self.__metadata.reflect(bind=self.__engine)

    def put(self, item):
        """
        Insert item in SQL table
        """
        if isinstance(item, type):
            msg = f"Item {item} is a class but must be instance of class"
            raise GeneralMemoryError(msg)
        msg = f"Item {item} does not resemble namedtuple instance"
        table = getattr(item, "__class__", False)
        table = getattr(table, "__name__", False)
        if not table:
            raise GeneralMemoryError(msg)
        table = table.lower()
        if table not in self.__metadata.tables:
            self.__create_table(table, item)
        table = self.__metadata.tables[table]
        for i in [i for i in dir(item) if i.startswith("add_")]:
            item = item._replace(**{i[4:]: getattr(item, i)()})
        if getattr(item, "id", False):
            stmt = sa.select(table)
            stmt = stmt.where(table.c.id == item.id)
            with self.__engine.connect() as conn:
                rows = conn.execute(stmt)
            if rows.first():
                return
        stmt = table.insert()
        stmt = stmt.values(item)
        with self.__engine.connect() as conn:
            with conn.begin():
                conn.execute(stmt)

    def reset(self):
        """
        Removes all data and tables
        """
        self.__metadata.drop_all(bind=self.__engine)
        self.__metadata.clear()

    def clean_all_data(self):
        """
        Removes all data and restores memory with all tables
        """
        self.__metadata.drop_all(bind=self.__engine)
        self.__metadata.create_all(bind=self.__engine)
