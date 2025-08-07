import os
import dotenv
import streamlit as st
import json

from pytidb import TiDBClient
from pytidb.schema import FullTextField, TableModel, Field

# Load environment variables.
dotenv.load_dotenv()

# Connect to TiDB database.
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "pytidb_fulltext_demo"),
    ensure_db=True,
)


# Create stock items table.
class Item(TableModel):
    __tablename__ = "items"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    title: str = FullTextField()
    language: str = Field(max_length=10)


table = db.open_table(Item)
if table is None:
    with st.spinner("Loading sample items, it may take a while..."):
        table = db.create_table(schema=Item, if_exists="overwrite")
        if table.rows() == 0:
            with open("sample_items.json", "r", encoding="utf-8") as f:
                sample_items = json.load(f)
            table.bulk_insert([Item(**item) for item in sample_items])


# Initialize UI.

# Sidebar.
with st.sidebar:
    st.logo(
        "../assets/logo-full.svg", size="large", link="https://pingcap.github.io/ai/"
    )
    st.markdown(
        """#### Overview

**Full-text search** is a technique that finds documents or data by matching keywords or phrases
within the entire text content.

TiDB provides full-text search capabilities for **massive datasets** with high performance and
built-in **multilingual support**.
    """
    )
    st.write("#### Settings")
    language = st.selectbox(
        "Select your preferred language for search:",
        [("English", "en"), ("Japanese", "ja"), ("Chinese", "zh")],
        format_func=lambda x: x[0],
    )[1]


# Main content.
st.markdown(
    '<h3 style="text-align: center; padding-top: 40px;">E-commerce Product Search</h3>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="text-align: center;">Search for phones, laptops, headphones, and more products</p>',
    unsafe_allow_html=True,
)

# Recommended keywords.
recommended_keywords = {
    "en": ["Bluetooth Headphone", "Gaming Laptop", "Senior Phone"],
    "ja": ["Bluetoothイヤホン", "ゲーミングノート", "シニア携帯"],
    "zh": ["蓝牙耳机", "游戏笔记本", "老年手机"],
}


def render_recommended_keywords(language):
    html = "<span style='color:gray'>Try searching for: </span>"
    keywords = recommended_keywords[language]
    for keyword in keywords:
        html += f'<b>"{keyword}"</b>'
        if keyword != keywords[-1]:
            html += ", "
    return st.markdown(html, unsafe_allow_html=True)


# Search form.
with st.form("search_form"):
    col1, col2 = st.columns([6, 1])
    with col1:
        query_text = st.text_input(
            "Keywords:",
            placeholder="Enter your search query",
            label_visibility="collapsed",
        )
        render_recommended_keywords(language)
    with col2:
        submitted = st.form_submit_button("Search")

# Search results.
if submitted:
    with st.spinner("Searching documents containing the keyword..."):
        # 👇 Perform full-text search via TiDB client.
        df = (
            table.search(query_text, search_type="fulltext")
            .text_column("title")
            .filter(Item.language == language)
            .limit(10)
            .to_pandas()
        )

        if len(df) > 0:
            st.markdown(
                f'Found <b>{len(df)}</b> results for <b>"{query_text}"</b>',
                unsafe_allow_html=True,
            )
            df = df.drop(["language", "_score"], axis=1)
            st.dataframe(df, hide_index=True)
        else:
            st.empty()
