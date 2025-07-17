import pytest
from sqlmodel import Session

from pytidb import Table, TiDBClient
from pytidb.schema import Field, TableModel


@pytest.fixture(scope="session")
def player_table(shared_client):
    class Player(TableModel):
        __tablename__ = "players"
        id: int = Field(primary_key=True)
        name: str = Field(max_length=20)
        balance: int = Field(default=0)

    table = shared_client.create_table(schema=Player, if_exists="overwrite")
    table.truncate()
    table.bulk_insert(
        [
            Player(id=1, name="Alice", balance=100),
            Player(id=2, name="Bob", balance=100),
        ]
    )
    return table


def test_db_client_commit(player_table: Table, shared_client: TiDBClient):
    with shared_client.session():
        initial_total_balance = shared_client.query(
            "SELECT SUM(balance) FROM players"
        ).scalar()

        # Transfer 10 coins from player 1 to player 2
        from_player_id = 1
        to_player_id = 2
        transfer_amount = 10
        shared_client.execute(
            "UPDATE players SET balance = balance + :inc WHERE id = :from_player_id",
            {"inc": transfer_amount, "from_player_id": from_player_id},
        )
        shared_client.execute(
            "UPDATE players SET balance = balance - :dec WHERE id = :to_player_id",
            {"dec": transfer_amount, "to_player_id": to_player_id},
        )

        final_total_balance = shared_client.query(
            "SELECT SUM(balance) FROM players"
        ).scalar()
        assert final_total_balance == initial_total_balance


def test_db_client_rollback(player_table: Table, shared_client: TiDBClient):
    with shared_client.session() as session:
        initial_balance_1 = shared_client.query(
            "SELECT balance FROM players WHERE id = 1"
        ).scalar()
        initial_balance_2 = shared_client.query(
            "SELECT balance FROM players WHERE id = 2"
        ).scalar()

        # Transfer 10 coins from player 1 to player 2
        from_player_id = 1
        to_player_id = 2
        transfer_amount = 10
        shared_client.execute(
            "UPDATE players SET balance = balance + :inc WHERE id = :from_player_id",
            {"inc": transfer_amount, "from_player_id": from_player_id},
        )
        shared_client.execute(
            "UPDATE players SET balance = balance - :dec WHERE id = :to_player_id",
            {"dec": transfer_amount, "to_player_id": to_player_id},
        )

        # Rollback to the initial state before the transaction beginning,
        session.rollback()

        final_balance_1 = shared_client.query(
            "SELECT balance FROM players WHERE id = 1"
        ).scalar()
        final_balance_2 = shared_client.query(
            "SELECT balance FROM players WHERE id = 2"
        ).scalar()
        assert initial_balance_1 == final_balance_1
        assert initial_balance_2 == final_balance_2


def test_local_session_commit(player_table: Table, shared_client: TiDBClient):
    player_id = 1
    player = player_table.get(player_id)
    expected_balance = player.balance + 1

    player_table.update(
        {
            "balance": player.balance + 1,
        },
        {"id": player_id},
    )

    player = player_table.get(player_id)
    assert player.balance == expected_balance


def test_local_session_rollback(player_table: Table, shared_client: TiDBClient):
    player_id = 1
    player = player_table.get(player_id)
    expected_balance = player.balance

    try:
        player_table.update(
            {
                "balance": player.balance + 2**31,
            },
            {"id": player_id},
        )
    except Exception as e:
        assert "Out of range" in str(e)

    player = player_table.get(player_id)
    assert player.balance == expected_balance


def test_context_session_commit(player_table: Table, shared_client: TiDBClient):
    with shared_client.session() as session:
        player_id = 1
        player = player_table.get(player_id)
        expected_balance = player.balance + 1

        player_table.update(
            {
                "balance": player.balance + 1,
            },
            {"id": player_id},
        )

        session.commit()

        player = player_table.get(player_id)
        assert player.balance == expected_balance


def test_context_session_rollback(player_table: Table, shared_client: TiDBClient):
    with shared_client.session() as session:
        player_id = 1
        player = player_table.get(player_id)
        expected_balance = player.balance

        player_table.update(
            {
                "balance": player.balance + 10,
            },
            {"id": player_id},
        )

        session.rollback()

        player = player_table.get(player_id)
        assert player.balance == expected_balance


def test_provided_session_commit(player_table: Table, shared_client: TiDBClient):
    with Session(shared_client._db_engine) as provided_session:
        with shared_client.session(provided_session=provided_session):
            player_id = 1
            player = player_table.get(player_id)
            expected_balance = player.balance + 1

            player_table.update(
                {
                    "balance": player.balance + 1,
                },
                {"id": player_id},
            )

            player = player_table.get(player_id)
            assert player.balance == expected_balance


def test_provided_session_rollback(player_table: Table, shared_client: TiDBClient):
    with Session(shared_client._db_engine) as provided_session:
        with shared_client.session(provided_session=provided_session):
            player_id = 1
            player = player_table.get(player_id)
            expected_balance = player.balance

            try:
                player_table.update(
                    {
                        "balance": player.balance + 2**31,
                    },
                    {"id": player_id},
                )
            except Exception as e:
                assert "Out of range" in str(e)

            player = player_table.get(player_id)
            assert player.balance == expected_balance
