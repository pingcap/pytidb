# Transaction

TiDB supports ACID transactions, which ensure data consistency and reliability:

- **Atomicity**: All operations in a transaction either complete entirely or have no effect at all
- **Consistency**: Transactions bring the database from one valid state to another
- **Isolation**: Concurrent transactions execute as if they were running sequentially
- **Durability**: Once committed, transaction changes persist even in case of system failure

A transaction is a sequence of SQL operations that are executed as a single atomic unit - they either all succeed or all fail together.

## Basic Usage

```python
with db.session() as session:
    initial_total_balance = session.query("SELECT SUM(balance) FROM players").scalar()

    # Transfer 10 coins from player 1 to player 2
    session.execute("UPDATE players SET balance = balance - 10 WHERE id = 1")
    session.execute("UPDATE players SET balance = balance + 10 WHERE id = 2")

    session.commit()
    # or session.rollback()

    final_total_balance = session.query("SELECT SUM(balance) FROM players").scalar()
    assert final_total_balance == initial_total_balance
```

## TiDB Transaction Features

- Supports isolation levels: READ COMMITTED, REPEATABLE READ (default), and SERIALIZABLE
- Optimistic transaction mode (default) and pessimistic transaction mode
- Distributed transactions with high performance and strong consistency
- Automatic retry mechanism for certain transaction conflicts

## See also

- [TiDB Develop Guide - Transaction](https://docs.pingcap.com/tidbcloud/dev-guide-transaction-overview/)
- [TiDB Docs- SQL Reference - Transactions](https://docs.pingcap.com/tidbcloud/transaction-overview/)