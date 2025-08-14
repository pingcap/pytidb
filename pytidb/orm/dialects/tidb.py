"""
TiDB Dialect
"""

import sqlalchemy
from sqlalchemy.dialects.mysql.base import MySQLCompiler, MySQLDDLCompiler
from sqlalchemy.dialects.mysql.pymysql import MySQLDialect_pymysql
from sqlalchemy.sql.ddl import CreateIndex
from sqlalchemy.sql import sqltypes
from sqlalchemy.sql import elements
from sqlalchemy.sql import functions
from sqlalchemy.sql import operators


class CreateIndexInline(CreateIndex):
    """DDL element for inline index creation within CREATE TABLE."""

    __visit_name__ = "create_index_inline"

    def __init__(self, element, if_not_exists=False):
        super().__init__(element, if_not_exists=if_not_exists)


class TiDBSQLCompiler(MySQLCompiler):
    """Custom SQL compiler for TiDB with enhanced CREATE TABLE support."""

    pass


class TiDBDDLCompiler(MySQLDDLCompiler):
    """Custom DDL compiler for TiDB with enhanced CREATE TABLE support."""

    def visit_create_table(self, create, **kw):
        table = create.element
        preparer = self.preparer

        text = "\nCREATE "
        if table._prefixes:
            text += " ".join(table._prefixes) + " "

        text += "TABLE "
        if create.if_not_exists:
            text += "IF NOT EXISTS "

        text += preparer.format_table(table) + " "

        create_table_suffix = self.create_table_suffix(table)
        if create_table_suffix:
            text += create_table_suffix + " "

        text += "("

        separator = "\n"

        # if only one primary key, specify it along with the column
        first_pk = False
        for create_column in create.columns:
            column = create_column.element
            try:
                processed = self.process(
                    create_column, first_pk=column.primary_key and not first_pk
                )
                if processed is not None:
                    text += separator
                    separator = ", \n"
                    text += "\t" + processed
                if column.primary_key:
                    first_pk = True
            except sqlalchemy.exc.CompileError as ce:
                raise sqlalchemy.exc.CompileError(
                    "(in table '%s', column '%s'): %s"
                    % (table.description, column.name, ce.args[0])
                ) from ce

        # Add table constraints
        const = self.create_table_constraints(
            table,
            _include_foreign_key_constraints=create.include_foreign_key_constraints,  # noqa
        )
        if const:
            text += separator + "\t" + const

        # Add indexes inline
        if hasattr(table, "indexes") and table.indexes:
            for index in table.indexes:
                try:
                    # Create a CreateIndexInline object and process it using self.process
                    create_index_inline = CreateIndexInline(index)
                    index_def = self.process(create_index_inline)
                    if index_def:
                        text += separator + "\t" + index_def
                        if separator == "\n":
                            separator = ", \n"
                except Exception:
                    # If index compilation fails, skip it and let it be created separately
                    pass

        text += "\n)%s\n\n" % self.post_create_table(table)
        return text

    def visit_create_column(self, create, first_pk=False, **kw):
        """Override visit_create_column to support inline column comment."""
        column = create.element

        if column.system:
            return None

        text = self.get_column_specification(column, first_pk=first_pk)
        const = " ".join(self.process(constraint) for constraint in column.constraints)
        if const:
            text += " " + const

        if column.comment is not None:
            comment = self.sql_compiler.render_literal_value(
                column.comment, sqltypes.String()
            )
            text += f" COMMENT {comment}"

        return text

    def _visit_create_index(self, create, inline=False, **kw):
        """Internal method to handle both inline and standalone CREATE INDEX."""
        # Copy from sqlalchemy.dialects.mysql.base.MySQLCompiler::visit_create_index
        index = create.element
        self._verify_index_table(index)
        preparer = self.preparer
        table = preparer.format_table(index.table)

        columns = [
            self.sql_compiler.process(
                (
                    elements.Grouping(expr)
                    if (
                        isinstance(expr, elements.BinaryExpression)
                        or (
                            isinstance(expr, elements.UnaryExpression)
                            and expr.modifier
                            not in (operators.desc_op, operators.asc_op)
                        )
                        or isinstance(expr, functions.FunctionElement)
                    )
                    else expr
                ),
                include_table=False,
                literal_binds=True,
            )
            for expr in index.expressions
        ]

        name = self._prepared_index_name(index)

        # Generate different text based on inline parameter
        if inline:
            # For inline index in CREATE TABLE, don't include CREATE, IF NOT EXISTS, or ON table
            text = ""
        else:
            # For standalone CREATE INDEX
            text = "CREATE "

        if index.unique:
            text += "UNIQUE "

        index_prefix = index.kwargs.get("%s_prefix" % "mysql", None)
        if index_prefix:
            text += index_prefix + " "

        text += "INDEX "

        if not inline:
            # Only add IF NOT EXISTS and table reference for standalone CREATE INDEX
            if create.if_not_exists:
                text += "IF NOT EXISTS "
            text += "%s ON %s " % (name, table)
        else:
            # For inline index, just add the name
            text += "%s " % name

        length = index.dialect_options.get("mysql", {}).get("length")
        if length is not None:
            if isinstance(length, dict):
                # length value can be a (column_name --> integer value)
                # mapping specifying the prefix length for each column of the
                # index
                columns = ", ".join(
                    (
                        "%s(%d)" % (expr, length[col.name])
                        if col.name in length
                        else (
                            "%s(%d)" % (expr, length[expr])
                            if expr in length
                            else "%s" % expr
                        )
                    )
                    for col, expr in zip(index.expressions, columns)
                )
            else:
                # or can be an integer value specifying the same
                # prefix length for all columns of the index
                columns = ", ".join("%s(%d)" % (col, length) for col in columns)
        else:
            columns = ", ".join(columns)

        text += "(%s)" % columns

        parser = index.dialect_options.get("mysql", {}).get("with_parser")
        if parser is not None:
            text += " WITH PARSER %s" % (parser,)

        using = index.dialect_options.get("mysql", {}).get("using")
        if using is not None:
            text += " USING %s" % (using)

        # Only add ADD_COLUMNAR_REPLICA_ON_DEMAND for standalone CREATE INDEX, not inline
        if (
            not inline
            and hasattr(index, "ensure_columnar_replica")
            and index.ensure_columnar_replica
        ):
            text += " ADD_COLUMNAR_REPLICA_ON_DEMAND"

        return text

    def visit_create_index(self, create, **kw):
        """Generate standalone CREATE INDEX statement."""
        return self._visit_create_index(create, inline=False, **kw)

    def visit_create_index_inline(self, create, **kw):
        """Generate inline index definition for CREATE TABLE statement."""
        return self._visit_create_index(create, inline=True, **kw)

    def visit_set_tiflash_replica(self, set_replica, **kw):
        """Generate ALTER TABLE ... SET TIFLASH REPLICA statement."""
        table = set_replica.table
        replica_count = set_replica.replica_count

        preparer = self.preparer
        table_name = preparer.format_table(table)

        return f"ALTER TABLE {table_name} SET TIFLASH REPLICA {replica_count}"


class TiDBDialect(MySQLDialect_pymysql):
    """Custom TiDB dialect with enhanced CREATE TABLE support."""

    name = "tidb"
    supports_comments = True
    inline_comments = True  # Enable inline comments
    supports_statement_cache = True  # Enable SQLAlchemy statement caching

    # Use our custom compilers
    statement_compiler = TiDBSQLCompiler
    ddl_compiler = TiDBDDLCompiler

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # TiDB specific configurations
        self.supports_comments = True
        self.inline_comments = True
