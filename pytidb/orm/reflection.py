import logging
from sqlalchemy.dialects.mysql.reflection import MySQLTableDefinitionParser


logger = logging.getLogger(__name__)


class TiDBTableDefinitionParser(MySQLTableDefinitionParser):
    """TiDB table definition parser."""

    def __init__(self, dialect, preparer):
        MySQLTableDefinitionParser.__init__(self, dialect, preparer)
