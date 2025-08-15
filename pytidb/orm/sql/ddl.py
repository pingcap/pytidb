import sqlalchemy
from sqlalchemy.sql.ddl import SchemaGenerator, SchemaDropper, CreateColumn, CreateIndex
from sqlalchemy.sql import sqltypes, elements, functions, operators
from sqlalchemy.ext.compiler import compiles

from pytidb.utils import TIDB_SERVERLESS_HOST_PATTERN
from ..indexes import CreateIndexInline
from ..tiflash_replica import SetTiFlashReplica, TiFlashReplica


class TiDBSchemaGenerator(SchemaGenerator):
    def visit_index(self, index, create_ok=False):
        if not create_ok and not self._can_create_index(index):
            return
        with self.with_ddl_events(index):
            self.is_tidb_serverless = TIDB_SERVERLESS_HOST_PATTERN.match(
                self.connection.engine.url.host
            )

            # Notice: Self-managed TiDB 8.5.0 does not support the ADD_COLUMNAR_REPLICA_ON_DEMAND parameter
            # in CREATE VECTOR INDEX statements, so TiFlash replicas need to be created manually.
            if index.ensure_columnar_replica and not index.is_tidb_serverless:
                TiFlashReplica(index.table, replica_count=1).create(self.connection)
                index.ensure_columnar_replica = False
            CreateIndex(index)._invoke_with(self.connection)

    def visit_tiflash_replica(self, tiflash_replica: TiFlashReplica):
        with self.with_ddl_events(tiflash_replica):
            SetTiFlashReplica(tiflash_replica)._invoke_with(self.connection)


class TiDBSchemaDropper(SchemaDropper):
    def visit_tiflash_replica(self, tiflash_replica: TiFlashReplica):
        with self.with_ddl_events(tiflash_replica):
            tiflash_replica.replica_count = 0
            SetTiFlashReplica(tiflash_replica)._invoke_with(self.connection)


# @compiles(CreateTable, "mysql")
def compile_create_table(create, compiler, **kw):
    """Enhanced CREATE TABLE compilation for TiDB with MySQL dialect."""
    table = create.element
    preparer = compiler.preparer

    text = "\nCREATE "
    if table._prefixes:
        text += " ".join(table._prefixes) + " "

    text += "TABLE "
    if create.if_not_exists:
        text += "IF NOT EXISTS "

    text += preparer.format_table(table) + " "

    create_table_suffix = compiler.create_table_suffix(table)
    if create_table_suffix:
        text += create_table_suffix + " "

    text += "("

    separator = "\n"

    # if only one primary key, specify it along with the column
    first_pk = False
    for create_column in create.columns:
        column = create_column.element
        try:
            processed = compiler.process(
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
    const = compiler.create_table_constraints(
        table,
        _include_foreign_key_constraints=create.include_foreign_key_constraints,  # noqa
    )
    if const:
        text += separator + "\t" + const

    # Add indexes inline
    if hasattr(table, "indexes") and table.indexes:
        # Import here to avoid circular imports
        from pytidb.orm.indexes import CreateIndexInline

        for index in table.indexes:
            try:
                # Create a CreateIndexInline object and process it using compiler.process
                create_index_inline = CreateIndexInline(index)
                index_def = compiler.process(create_index_inline)
                if index_def:
                    text += separator + "\t" + index_def
                    if separator == "\n":
                        separator = ", \n"
            except Exception:
                # If index compilation fails, skip it and let it be created separately
                pass

    text += "\n)%s\n\n" % compiler.post_create_table(table)
    return text


@compiles(CreateColumn, "mysql")
def compile_create_column(create, compiler, first_pk=False, **kw):
    """Override visit_create_column to support inline column comment."""
    column = create.element

    if column.system:
        return None

    text = compiler.get_column_specification(column, first_pk=first_pk)
    const = " ".join(compiler.process(constraint) for constraint in column.constraints)
    if const:
        text += " " + const

    if column.comment is not None:
        comment = compiler.sql_compiler.render_literal_value(
            column.comment, sqltypes.String()
        )
        text += f" COMMENT {comment}"

    return text


@compiles(CreateIndex, "mysql")
def compile_create_index(create, compiler, **kw):
    """Enhanced CREATE INDEX compilation for TiDB with MySQL dialect."""
    return _compile_create_index(create, compiler, inline=False, **kw)


@compiles(CreateIndexInline, "mysql")
def compile_create_index_inline(create, compiler, **kw):
    """Enhanced inline index compilation for TiDB with MySQL dialect."""
    return _compile_create_index(create, compiler, inline=True, **kw)


def _compile_create_index(create, compiler, inline=False, **kw):
    """Internal method to handle both inline and standalone CREATE INDEX."""
    # Copy from sqlalchemy.dialects.mysql.base.MySQLCompiler::visit_create_index
    index = create.element
    compiler._verify_index_table(index)
    preparer = compiler.preparer
    table = preparer.format_table(index.table)

    columns = [
        compiler.sql_compiler.process(
            (
                elements.Grouping(expr)
                if (
                    isinstance(expr, elements.BinaryExpression)
                    or (
                        isinstance(expr, elements.UnaryExpression)
                        and expr.modifier not in (operators.desc_op, operators.asc_op)
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

    name = compiler._prepared_index_name(index)

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
        and index.is_tidb_serverless
    ):
        text += " ADD_COLUMNAR_REPLICA_ON_DEMAND"

    return text


@compiles(SetTiFlashReplica, "mysql")
def compile_set_tiflash_replica(set_tiflash_replica, compiler, **kw):
    """Generate ALTER TABLE ... SET TIFLASH REPLICA statement."""
    table = set_tiflash_replica.element.table
    replica_count = set_tiflash_replica.element.replica_count

    preparer = compiler.preparer
    table_name = preparer.format_table(table)

    return f"ALTER TABLE {table_name} SET TIFLASH REPLICA {replica_count}"
