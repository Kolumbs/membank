"""Defines interface class and functions for library."""

import dataclasses as data
import os
import urllib.parse

import sqlalchemy as sa

import membank.datamethods as meths
from membank import datamapper
from membank import errors as e
from membank.utils import assert_table_name, get_class_name


def bundle_item(item):
    """Scan dataclass item for special metadata key value.

    Return a dict of found item.
    """
    meta = {}
    for i in data.fields(item):
        if "key" in i.metadata:
            meta["key"] = i.name
    return meta


class MemoryBlob:
    """Allows to access memory get method dynamically.

    Exposes a get method that dynamically allows to access memory using
    dataclass lowercased name:
    - as a method
    - as a first function argument
    """

    def __init__(self, parent):
        """Initialise blob with parent and getters."""
        self.__parent = parent
        self.__getters = {}

    def __make_getter_by_name(self, name):
        """Make getter by name."""

        def getter(**kw):
            """Get item from memory."""
            try:
                table = self.__parent._get_sql_table(name)
            except e.MemoryTableDoesNotExist:
                return None
            classload = self.__parent._get_class(name)
            if not classload:
                return None
            args = [table, self.__parent._get_engine(), classload]
            try:
                return meths.get_item(*args, **kw)
            except e.MemoryOutOfSyncError:
                self.__parent.sync(args[2])
                args[0] = self.__parent._get_sql_table(name)
                return meths.get_item(*args, **kw)

        return getter

    def __getattr__(self, name):
        """Get memory attribute."""
        if name not in self.__getters:
            self.__getters[name] = self.__make_getter_by_name(name)
        return self.__getters[name]

    def __call__(self, *instructions, **kargs):
        """Fetch result from memory.

        Expects a table name or a table and a comparison as first
        argument.
        """
        filtering = []
        previous_name = ""
        if len(instructions) == 0:
            msg = "There must be at least one valid comparison to get items"
            raise e.GeneralMemoryError(msg)
        for instruction in instructions:
            match instruction:
                case sql_table, sql_operation:
                    table_name = getattr(sql_table, "name", False)
                    if table_name:
                        filtering.append(sql_operation)
                    else:
                        return []
                case table_name:
                    try:
                        sql_table = self.__parent._get_sql_table(table_name)
                    except e.MemoryTableDoesNotExist:
                        return []
            if previous_name and previous_name != table_name:
                raise e.MemoryFilteringError(table_name, previous_name)
            previous_name = table_name
        return_class = self.__parent._get_class(previous_name)
        try:
            args = [
                sql_table,
                self.__parent._get_engine(),
                return_class,
            ]
            return meths.get_list(*args, *filtering, **kargs)
        except e.MemoryOutOfSyncError:
            self.__parent.sync(return_class)
            args[0] = self.__parent._get_sql_table(previous_name)
            return meths.get_list(*args, *filtering, **kargs)


def assert_path(path, db_type):
    """Check for valid path, raise GeneralError if any issue."""
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
        raise e.GeneralMemoryError(msg)


class LoadMemory:
    """Loads memory and provides methods to create, change and access it."""

    def __init__(self, url: bool = False, debug: bool = False):
        """Initialise memory with base settings.

        debug - more verbose logging
        url - resource locator according to RFC-1738 with scheme to designate database
        type to be used, e.g. sqlite, postgresql, berkeleydb and scheme specific part
        always follow either Common Internet Scheme Syntax or using File scheme part

        Special note on relative vs. absolute file path handling
        As RFC-1738 does not allow relative file paths, special notation is used only for
        local file based access databases e.g. sqlite, berkeleydb. To make relative path,
        host location of file path must be used i.e. scheme://{relative_path}. For absolute
        paths host part must be empty i.e. scheme:///{absolute_path}
        """
        if not url:
            url = "sqlite://:memory:"
        try:
            url = urllib.parse.urlparse(url)
        except AttributeError:
            raise e.GeneralMemoryError(f"Url '{url}' is not valid") from AttributeError
        if url.scheme in ["sqlite"]:
            path = url.netloc + url.path
            assert_path(path, url.scheme)
            url = sa.engine.URL.create(
                drivername=url.scheme,
                database=path,
            )
            self.__engine = sa.create_engine(
                url,
                echo=debug,
                future=True,
            )
        else:
            raise e.GeneralMemoryError(
                f"Such database type {url.scheme} is not supported"
            )
        self.get = MemoryBlob(self)
        self.__refresh_state()
        self.__classmap = datamapper.Mapper(self.__engine, self.__metadata)

    def __refresh_state(self):
        """Refresh metadata and dataclass."""
        self.__metadata = sa.MetaData()
        self.__metadata.reflect(bind=self.__engine)

    def __getattr__(self, name):
        """Fetch comparison method."""
        return meths.FilterOperator(name, self.__metadata)

    def _get_sql_table(self, name):
        """Return SQL table."""
        if name not in self.__metadata.tables:
            raise e.MemoryTableDoesNotExist(name)
        return self.__metadata.tables[name]

    def _get_engine(self):
        """Return engine."""
        return self.__engine

    def _get_class(self, name):
        """Return dataclass."""
        return self.__classmap.get_class(name)

    def delete(self, item):
        """Delete item in SQL table."""
        table = assert_table_name(item)
        if table not in self.__metadata.tables:
            msg = f"Memory '{item}' cannot be deleted as table '{table}' does not exist"
            raise e.GeneralMemoryError(msg)
        table = self.__metadata.tables[table]
        meths.delete_item(table, self.__engine, **data.asdict(item))

    def put(self, item):
        """Insert item in SQL table."""
        table = assert_table_name(item)
        if table not in self.__metadata.tables or table == "__meta_dataclasses__":
            if table in dir(self) or table == "__meta_dataclasses__":
                msg = (
                    f"Memory {item} cannot be created, such name is reserved by membank"
                )
                raise e.GeneralMemoryError(msg)
            meths.create_table(table, item, self.__engine)
        classload = self.__classmap.get_class(table)
        if not classload or classload != item.__class__:
            self.__classmap.put_class(table, item.__class__)
            self.__refresh_state()
        sql_table = self._get_sql_table(table)
        meta = bundle_item(item)
        key = meta["key"] if "key" in meta else None
        try:
            meths.update_item(sql_table, self._get_engine(), item, key)
        except e.MemoryOutOfSyncError:
            self.sync(self._get_class(table))
            sql_table = self._get_sql_table(table)
            meths.update_item(sql_table, self._get_engine(), item, key)

    def sync(self, obj):
        """Synchronise obj with SQL table."""
        table = get_class_name(obj)
        self.__classmap.put_class(table, obj)
        table = self.__metadata.tables[table]
        meths.sync_table(table, self._get_engine(), obj)
        self.__refresh_state()

    def reset(self):
        """Remove all data and tables."""
        self.__metadata.drop_all(bind=self.__engine)
        self.__metadata.clear()
        self.__classmap = datamapper.Mapper(self.__engine, self.__metadata)

    def clean_all_data(self):
        """Remove all data and restores memory with all tables."""
        tables_to_drop = dict(self.__metadata.tables)
        tables_to_drop.pop("__meta_dataclasses__")
        self.__metadata.drop_all(bind=self.__engine, tables=tables_to_drop.values())
        self.__metadata.create_all(bind=self.__engine)
