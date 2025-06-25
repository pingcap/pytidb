from sqlalchemy.sql.ddl import SchemaGenerator, CreateIndex
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import elements, operators, functions


@compiles(CreateIndex, "mysql")
def compile_create_index(create, compiler, **kw):
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

    text = "CREATE "
    if index.unique:
        text += "UNIQUE "

    index_prefix = index.kwargs.get("%s_prefix" % compiler.dialect.name, None)
    if index_prefix:
        text += index_prefix + " "

    text += "INDEX "
    if create.if_not_exists:
        text += "IF NOT EXISTS "
    text += "%s ON %s " % (name, table)

    length = index.dialect_options[compiler.dialect.name]["length"]
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

    parser = index.dialect_options[compiler.dialect.name]["with_parser"]
    if parser is not None:
        text += " WITH PARSER %s" % (parser,)

    using = index.dialect_options[compiler.dialect.name]["using"]
    if using is not None:
        text += " USING %s" % (using)

    if hasattr(index, "ensure_columnar_replica") and index.ensure_columnar_replica:
        text += " ADD_COLUMNAR_REPLICA_ON_DEMAND"

    return text


class CreateVectorIndex(CreateIndex):
    def __init__(self, element, if_not_exists=False):
        super().__init__(element, if_not_exists=if_not_exists)


class TiDBSchemaGenerator(SchemaGenerator):
    def visit_vector_index(self, index, create_ok=False):
        if not create_ok and not self._can_create_index(index):
            return
        with self.with_ddl_events(index):
            CreateVectorIndex(index)._invoke_with(self.connection)


@compiles(CreateVectorIndex)
def compile_create_vector_index(element, compiler, **kw):
    index = element.index
    table_name = index.table.name
    column_name = index.columns[0].name
    distance_metric = index.distance_metric
    algorithm = index.algorithm
    distance_metric_str = f"({distance_metric.to_sql_func()}({column_name}))"

    sql = f"CREATE VECTOR INDEX {index.name} ON {table_name} ({distance_metric_str}) USING {algorithm}"
    if index.ensure_columnar_replica:
        sql += " ADD_COLUMNAR_REPLICA_ON_DEMAND"
    return sql
