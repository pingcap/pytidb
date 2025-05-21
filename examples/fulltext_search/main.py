import os

import dotenv
import litellm
import streamlit as st
import pandas as pd

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.datatype import Text

dotenv.load_dotenv()
litellm.drop_params = True

db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
)
# database_url = "mysql://username:password@host:port/database"
# db = TiDBClient.connect(database_url)`


# Create document table


class StockItem(TableModel, table=True):
    __tablename__ = "stock_items"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    title: str = Field(sa_type=Text)


table = db.create_table(schema=StockItem)

if not table.has_fts_index("title"):
    table.create_fts_index("title")

# Ingest sample documents

sample_documents = [
    {"id": 1, "title": "イヤホン bluetooth ワイヤレスイヤホン "},
    {"id": 2, "title": "完全ワイヤレスイヤホン/ウルトラノイズキャンセリング 2.0 "},
    {
        "id": 3,
        "title": "ワイヤレス ヘッドホン Bluetooth 5.3 65時間再生 ヘッドホン 40mm HD ",
    },
    {"id": 4, "title": "楽器用 オンイヤーヘッドホン 密閉型【国内正規品】"},
    {
        "id": 5,
        "title": "ワイヤレスイヤホン ハイブリッドANC搭载 40dBまでアクティブノイズキャンセル",
    },
    {"id": 6, "title": "Lightweight Bluetooth Earbuds with 48 Hours Playtime"},
    {
        "id": 7,
        "title": "True Wireless Noise Cancelling Earbuds - Compatible with Apple & Android, Built-in Microphone",
    },
    {"id": 8, "title": "In-Ear Earbud Headphones with Mic, Black"},
    {
        "id": 9,
        "title": "Wired Headphones, HD Bass Driven Audio, Lightweight Aluminum Wired in Ear Earbud Headphones",
    },
    {"id": 10, "title": "LED Light Bar, Music Sync RGB Light Bar, USB Ambient Lamp"},
    {
        "id": 11,
        "title": "无线消噪耳机-黑色 手势触控蓝牙降噪 主动降噪头戴式耳机（智能降噪 长久续航）",
    },
    {
        "id": 12,
        "title": "专业版USB7.1声道游戏耳机电竞耳麦头戴式电脑网课办公麦克风带线控",
    },
    {"id": 13, "title": "投影仪家用智能投影机便携卧室手机投影"},
    {"id": 14, "title": "无线蓝牙耳机超长续航42小时快速充电 流光金属耳机"},
    {"id": 15, "title": "皎月银 国家补贴 心率血氧监测 蓝牙通话 智能手表 男女表"},
]

if table.rows() == 0:
    table.bulk_insert([StockItem(**doc) for doc in sample_documents])


# Streamlit UI
st.title("🔍 Fulltext Search Demo")
query_limit = st.sidebar.slider("query limit", min_value=1, max_value=20, value=10)

st.write(
    "Input your search query (e.g. 'Bluetooth Headphone','イヤホン bluetooth', '蓝牙耳机')"
)


query_text = st.text_input("", "")

if st.button("Search") and query_text:
    with st.spinner("Searching documents containing the keyword..."):
        df = (
            table.search(query_text, search_type="fulltext")
            .limit(query_limit)
            .to_pandas()
        )

        if df.size > 0:
            st.write("### Search results:")
            df = df.drop(columns=["_score"])
            st.dataframe(df)
        else:
            st.info("No results found")
else:
    with st.spinner("Loading all documents..."):
        items = table.query()
        df = pd.DataFrame([{"id": item.id, "title": item.title} for item in items])
        st.write("### All documents:")
        st.dataframe(df)
