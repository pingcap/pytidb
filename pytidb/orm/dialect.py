from sqlalchemy import util
from sqlalchemy.dialects.mysql import pymysql

from pytidb.orm.vector import VECTOR
from pytidb.orm.reflection import TiDBTableDefinitionParser


class TiDBDialect(pymysql.MySQLDialect_pymysql):
    """
    TiDB dialect implementation for SQLAlchemy.

    This dialect extends the PyMySQL MySQL dialect to provide TiDB-specific functionality
    while maintaining compatibility with the MySQL protocol.
    """

    name = "tidb"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ischema_names["VECTOR"] = VECTOR

    @util.memoized_property
    def _tabledef_parser(self):
        """return the TiDBTableDefinitionParser, generate if needed.

        The deferred creation ensures that the dialect has
        retrieved server version information first.

        """
        preparer = self.identifier_preparer
        return TiDBTableDefinitionParser(self, preparer)
