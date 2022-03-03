"""
Defines interface class and functions for library
"""
import os
import typing
import urllib.parse

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


class GeneralMemoryError(Exception):
    """
    All general errors in memory interface
    """


# pylint: disable=R0903
class MemoryBlob():
    """
    Allows to access generically any table
    """

    def __init__(self, table, conn):
        """
        Initialises table and session
        """
        self.table = table
        self.conn = conn

    def __call__(self, **filtering):
        stmt = sa.select(self.table)
        if filtering:
            for key, value in filtering.items():
                stmt = stmt.where(getattr(self.table.c, key) == value)
        cursor = self.conn.execute(stmt).all()
        return cursor[0] if cursor else None


# pylint: disable=R0903
class MemoryPut():
    """
    Allows to add memory item to any table
    """

    def __init__(self, table, conn):
        """
        Initialises table and session
        """
        self.table = table
        self.conn = conn

    def __call__(self, item):
        for i in [i for i in dir(item) if i.startswith("add_")]:
            item = item._replace(**{i[4:]: getattr(item, i)()})
        if getattr(item, "id", False):
            stmt = sa.select(self.table)
            stmt = stmt.where(self.table.c.id == item.id)
            rows = self.conn.execute(stmt)
            if rows.first():
                return
        stmt = self.table.insert()
        stmt = stmt.values(item)
        self.conn.execute(stmt)
        self.conn.commit()


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
            self.__engine__ = sa.create_engine(
                url,
                echo = debug,
                future = True,
            )
            self.__conn__ = self.__engine__.connect()
            self.__conn__.__enter__()
            ctx = MigrationContext.configure(self.__conn__)
            self.__alembic__ = Operations(ctx)
            self.__metadata__ = sa.MetaData()
        else:
            raise GeneralMemoryError(f"Such database type {url.scheme} is not supported")
        self._load_attributes()

    def _load_attributes(self):
        """
        Loads all memory attributes
        """
        self.__metadata__.reflect(bind=self.__engine__)
        self.get = Get(self.__conn__, self.__metadata__)
        self.put = Put(self.__conn__, self.__metadata__)

    def create(self, *attributes):
        """
        Adds a memory attribute. Memory attribute must resemble namedtuple
        In database words this adds a new Table
        If 'id' is not given in attributes, it is automatically added as a reference
        to be able to get back specific memory item
        """
        for mem in attributes:
            try:
                table = mem.__name__
                annotations = dict(mem.__annotations__)
                fields = list(mem._fields)
            except AttributeError:
                msg = "Creating new table requires namedtuple. "
                msg += f"Instead got {mem}"
                raise GeneralMemoryError(msg) from AttributeError
            for i in [i for i in dir(mem) if i.startswith("add_")]:
                if not i[4:] in fields:
                    msg = f"Field {i[4:]} is not defined to be used in function {i}"
                    raise GeneralMemoryError(msg)
            table = str(table).lower()
            cols = []
            for name in fields:
                col_type = annotations[name]
                if col_type in (float, typing.Union[float, None]):
                    col_type = sa.Float
                elif col_type in (str, typing.Union[str, None]):
                    col_type = sa.String
                else:
                    raise GeneralMemoryError(f"Type {col_type} is not supported")
                col = sa.Column(name, col_type)
                cols.append(col)
            if "id" not in fields:
                cols.append(sa.Column("id", sa.Integer))
            cols.append(sa.PrimaryKeyConstraint('id'))
            cols.append(sa.Index("idx_id", "id"))
            # pylint: disable=E1101
            try:
                self.__alembic__.create_table(table, *cols)
            except sa.exc.OperationalError as error:
                msg = error.args[0]
                if "table" in msg and "already exists" in msg:
                    msg = f"Table {table} already exists. Use change instead"
                    raise GeneralMemoryError(msg) from None
        self.__metadata__.reflect(bind=self.__engine__)

    def close(self):
        """
        Closes all open objects
        """
        self.__conn__.__exit__(None, None, None)

    def reset(self):
        """
        Removes all data and tables
        """
        self.__metadata__.drop_all(bind=self.__engine__)

    def clean_all_data(self):
        """
        Removes all data and restores memory with all tables
        """
        self.__metadata__.drop_all(bind=self.__engine__)
        self.__metadata__.create_all(bind=self.__engine__)


class CommonMemoryHandling():
    """
    Methods that are common to Get and Set classes
    """

    def __init__(self, conn, metadata):
        """
        conn is connection object to get data from database
        """
        self.__metadata__ = metadata
        self.__conn__ = conn

    def _fetch_table(self, name):
        """
        returns Table object
        """
        try:
            table = self.__metadata__.tables[name]
            return table
        except ValueError:
            raise OSError(f"{name} is not found in memory") from ValueError


class Get(CommonMemoryHandling):
    """
    Support class for getting different memory items
    """

    def __getattr__(self, name):
        table = self._fetch_table(name)
        return MemoryBlob(table, self.__conn__)


class Put(CommonMemoryHandling):
    """
    Support class for writing memory items
    """

    def __getattr__(self, name):
        table = self._fetch_table(name)
        return MemoryPut(table, self.__conn__)
