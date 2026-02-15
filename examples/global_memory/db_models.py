import os
from dotenv import load_dotenv
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.datatype import TEXT, DATETIME, BOOLEAN, INT
from datetime import datetime

load_dotenv()


class ChatSessionDB(TableModel):
    __tablename__ = "chat_sessions"

    session_id: str = Field(primary_key=True)
    start_time: datetime = Field(sa_type=DATETIME)
    is_active: bool = Field(sa_type=BOOLEAN)
    memory_enabled: bool = Field(sa_type=BOOLEAN)
    messages: str = Field(sa_type=TEXT)  # JSON string of messages
    previous_summaries: str = Field(sa_type=TEXT)  # JSON string of summaries


class SessionSummaryDB(TableModel):
    __tablename__ = "session_summaries"

    session_id: str = Field(primary_key=True)
    summary: str = Field(sa_type=TEXT)
    message_count: int = Field(sa_type=INT)
    start_time: datetime = Field(sa_type=DATETIME)
    end_time: datetime = Field(sa_type=DATETIME)


class TiDBConnection:
    _instance = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TiDBConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._db is None:
            self._db = TiDBClient.connect(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", "4000")),
                username=os.getenv("DB_USERNAME"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_DATABASE"),
                ensure_db=True,
            )

            # Create tables if they don't exist
            self.sessions_table = self._db.create_table(
                schema=ChatSessionDB, if_exists="overwrite"
            )
            self.summaries_table = self._db.create_table(
                schema=SessionSummaryDB, if_exists="overwrite"
            )

    @property
    def db(self):
        return self._db

    @property
    def sessions_table(self):
        return self._sessions_table

    @sessions_table.setter
    def sessions_table(self, value):
        self._sessions_table = value

    @property
    def summaries_table(self):
        return self._summaries_table

    @summaries_table.setter
    def summaries_table(self, value):
        self._summaries_table = value
