"""
Defines interface class and functions for library
"""
import dataclasses as data
import os
import urllib.parse

import sqlalchemy as sa

from membank import datamapper
import membank.datamethods as meths
from membank.errors import GeneralMemoryError, MemoryFilteringError


def bundle_item(item):
    """
    Scans metadata from item.fields and returns a dict of found items
    """
    meta = {}
    for i in data.fields(item):
        if "key" in i.metadata:
            meta["key"] = i.name
    return meta

def assert_correct_types(instance):
    """
    Veriffies that instance is a dataclass instance
    Verifies that instance has all fields as per annotated types
    Raises GeneralMemoryError otherwise
    """
    if isinstance(instance, type):
        msg = f"Item {instance} is a class but must be instance of class"
        raise GeneralMemoryError(msg)
    if not data.is_dataclass(instance):
        msg = f"Item {instance} must be instance of dataclass"
        raise GeneralMemoryError(msg)
    for field in data.fields(instance):
        field_val = getattr(instance, field.name)
        if not isinstance(field_val, field.type):
            if field.type == float and isinstance(field_val, int):
                continue
            msg = f"Field '{field.name}' is not of type {field.type}"
            raise GeneralMemoryError(msg)


# pylint: disable=R0903
class Attributer():
    """
    Wraps handling attribute calls for get
    """

    def __init__(self, table, engine, metadata, dataclass):
        self.__engine = engine
        self.__metadata = metadata
        self.name = table
        self.__table = None
        self.__dataclass = dataclass

    def __call__(self, **kargs):
        if self.name not in self.__metadata.tables:
            self.__metadata.reflect(bind=self.__engine)
            if self.name not in self.__metadata.tables:
                return None
        self.__table = self.__metadata.tables[self.name]
        return_class = self.__dataclass.get_class(self.__table)
        return meths.get_item(self.__table, self.__engine, return_class, **kargs)


class MemoryBlob():
    """
    Allows to access generically put method attributes
    """

    def __init__(self, engine, metadata, dataclass):
        """
        Initialises attribute/table list
        """
        self.__attrs = {}
        self.__engine = engine
        self.__metadata = metadata
        self.__dataclass = dataclass

    def __getattr__(self, name):
        if name in self.__attrs:
            return self.__attrs[name]
        new_attr = Attributer(name, self.__engine, self.__metadata, self.__dataclass)
        self.__attrs[name] = new_attr
        return new_attr

    def __call__(self, *instructions, **kargs):
        filtering = []
        previous_name = ""
        for instruction in instructions:
            match instruction:
                case sql_table, sql_operation:
                    table_name = getattr(sql_table, "name", False)
                    if table_name:
                        filtering.append(sql_operation)
                    else:
                        return []
                case table_name:
                    if not table_name in self.__metadata.tables:
                        return []
                    sql_table = self.__metadata.tables[table_name]
            if previous_name and previous_name != table_name:
                raise MemoryFilteringError(table_name, previous_name)
            previous_name = table_name
        stmt = meths.make_stmt(sql_table, *filtering, **kargs)
        return_class = self.__dataclass.get_class(sql_table)
        return meths.get_from_sql(return_class, stmt, self.__engine)

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
        try:
            url = urllib.parse.urlparse(url)
        except AttributeError:
            raise GeneralMemoryError(f"Url '{url}' is not valid") from AttributeError
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
        self.__metadata.reflect(bind=self.__engine)
        self.__dataclass = datamapper.Mapper(self.__engine, self.__metadata)
        self.get = MemoryBlob(self.__engine, self.__metadata, self.__dataclass)

    def __getattr__(self, name):
        """
        Fetches comparison method
        """
        return meths.FilterOperator(name, self.__metadata)

    def put(self, item):
        """
        Insert item in SQL table
        """
        assert_correct_types(item)
        table = getattr(item, "__class__", False)
        table = getattr(table, "__name__", False)
        table = table.lower()
        if table not in self.__metadata.tables or table == "__meta_dataclasses__":
            if table in dir(self) or table == "__meta_dataclasses__":
                msg = f"Memory {item} cannot be created because such name is reserved by membank"
                raise GeneralMemoryError(msg)
            meths.create_table(table, item, self.__engine)
            self.__dataclass.put_class(table, item.__class__)
            self.__metadata.reflect(bind=self.__engine)
        table = self.__metadata.tables[table]
        meta = bundle_item(item)
        key = meta["key"] if "key" in meta else None
        meths.update_item(table, self.__engine, item, key)

    def reset(self):
        """
        Removes all data and tables
        """
        self.__metadata.drop_all(bind=self.__engine)
        self.__metadata.clear()
        self.__dataclass = datamapper.Mapper(self.__engine, self.__metadata)

    def clean_all_data(self):
        """
        Removes all data and restores memory with all tables
        """
        tables_to_drop = dict(self.__metadata.tables)
        tables_to_drop.pop("__meta_dataclasses__")
        self.__metadata.drop_all(bind=self.__engine, tables=tables_to_drop.values())
        self.__metadata.create_all(bind=self.__engine)
