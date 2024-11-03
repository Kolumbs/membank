"""Connection utlity for SQLAlchemy and asyncpg."""

import json
from collections import namedtuple

import asyncpg
import sqlalchemy as sa


async def asyncpg_custom_types(conn):
    """Return custom types for asyncpg."""
    await conn.set_type_codec(
        "json",
        encoder=lambda x: x,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "jsonb",
        encoder=lambda x: x,
        decoder=json.loads,
        schema="pg_catalog",
    )


# pylint: disable=too-few-public-methods
class NamedRecord(asyncpg.Record):
    """Record class that supports namedtuple like behaviour."""

    def __getattr__(self, key):
        """Return value for key."""
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None


class SQLAlchemyResult:
    """Result class that supports some of the SQLAlchemy result methods.

    Object is returned from asyncpg execution, e.g session.execute
    """

    def __init__(self, result):
        """Load object with result from asyncpg execution."""
        self._mapping = result

    def first(self):
        """Return first row."""
        return self._mapping[0] if self._mapping else None

    def __iter__(self):
        """Return iterator."""
        return iter(self._mapping)

    def rowcount(self):
        """Return row count."""
        return len(self._mapping)


class SQLAlchemyDBAPI:
    """SQlAlchemy DBAPI silencer."""

    def cursor(self):
        """Return nothing."""


class SQLAlchemySupportedConnection(asyncpg.connection.Connection):
    """Connection class that supports SQLAlchemy stmt objects to be executed."""

    dialect = sa.dialects.postgresql.asyncpg.PGDialect_asyncpg()

    async def execute(self, query, *args, timeout=300):
        """Execute statement.

        If query appears to be SQLAlchemy stmt object, convert it to string.
        If query appears to be SQLAlchemy ORM object, convert it to valid stmt.
        """
        if isinstance(query, sa.sql.base.Executable):
            compiled_query = query.compile(
                dialect=sa.dialects.postgresql.asyncpg.PGDialect_asyncpg()
            )
            ctx = self.dialect.execution_ctx_cls._init_compiled(
                self.dialect,
                self,
                dbapi_connection=SQLAlchemyDBAPI(),
                execution_options={},
                compiled=compiled_query,
                parameters=tuple(),
                invoked_statement=None,
                extracted_parameters={},
            )
            stmt = ctx.statement
            params = ctx.parameters[0]
            if isinstance(query, sa.sql.expression.Delete):
                result = await super().execute(stmt, *params, timeout=timeout)
                SQLDelete = namedtuple("SQLDelete", ["rowcount"])
                rowcount = int(result.replace("DELETE ", ""))
                return SQLDelete(rowcount)
            return SQLAlchemyResult(await super().fetch(stmt, *params, timeout=timeout))
        return await super().execute(query, *args, timeout=timeout)
