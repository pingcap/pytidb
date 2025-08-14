from sqlalchemy.sql.ddl import (
    SchemaGenerator,
    CreateTable,
)


class TiDBSchemaGenerator(SchemaGenerator):
    def visit_table(
        self,
        table,
        create_ok=False,
        include_foreign_key_constraints=None,
        _is_metadata_operation=False,
    ):
        if not create_ok and not self._can_create_table(table):
            return

        with self.with_ddl_events(
            table,
            checkfirst=self.checkfirst,
            _is_metadata_operation=_is_metadata_operation,
        ):
            for column in table.columns:
                if column.default is not None:
                    self.traverse_single(column.default)

            if not self.dialect.supports_alter:
                # e.g., don't omit any foreign key constraints
                include_foreign_key_constraints = None

            CreateTable(
                table,
                include_foreign_key_constraints=(include_foreign_key_constraints),
            )._invoke_with(self.connection)

    def visit_set_tiflash_replica(self, set_replica, checkfirst=False):
        """Visit a SetTiFlashReplica DDL element."""
        if checkfirst:
            # Could add logic to check current replica count here
            pass

        # Generate and execute the DDL statement
        from sqlalchemy import text

        compiler = self.dialect.ddl_compiler(self.dialect, None)
        stmt_str = compiler.visit_set_tiflash_replica(set_replica)
        self.connection.execute(text(stmt_str))
