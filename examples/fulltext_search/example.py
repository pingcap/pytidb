import os
import dotenv
import json

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field, FullTextField


# Load environment variables
dotenv.load_dotenv()

# Connect to database with connection parameters
print("=== CONNECT TO DATABASE ===")
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "pytidb_fulltext_example"),
    ensure_db=True,
)
print("Database connected\n")

# Define table schema
print("=== CREATE TABLE ===")


class Item(TableModel):
    __tablename__ = "items"
    id: int = Field(primary_key=True)
    title: str = FullTextField(fts_parser="MULTILINGUAL")


table = db.create_table(schema=Item, if_exists="overwrite")
print("Table created\n")

# Insert data
print("=== INSERT DATA ===")
table.bulk_insert(
    [
        Item(
            id=1,
            title="Bluetooth Earphones, HiFi sound, 48h battery, Fast charge, Low latency",
        ),
        Item(
            id=2,
            title="Bluetooth 5.3 Headphones, Noise Cancelling, Immersive sound, Comfortable",
        ),
        Item(
            id=3,
            title="IPX7 Waterproof Earbuds, Sport ready, Touch control, High-quality music",
        ),
        Item(
            id=4,
            title="Sports Earbuds, Secure fit, Sweatproof, Long battery, Workout support",
        ),
        Item(
            id=5,
            title="Wired Headphones, Studio-grade, HD sound, Comfortable, Pro music experience",
        ),
        Item(id=6, title="Bluetoothイヤホン HiFi音質 48hバッテリー 急速充電 低遅延"),
        Item(
            id=7,
            title="Bluetooth5.3ヘッドホン ノイズキャンセリング 没入サウンド 快適装着",
        ),
        Item(id=8, title="IPX7防水イヤホン スポーツ対応 タッチ操作 高音質音楽"),
        Item(
            id=9,
            title="スポーツイヤホン 安定装着 防汗 長持ちバッテリー ワークアウト対応",
        ),
        Item(id=10, title="有線ヘッドホン スタジオ級 HDサウンド 快適装着 プロ音楽体験"),
        Item(id=11, title="无线蓝牙耳机 HiFi音质 48小时超长续航 快速充电 低延迟"),
        Item(
            id=12,
            title="蓝牙5.3降噪头戴式耳机 杜比全景声 沉浸音效 舒适佩戴 畅享静谧音乐时光",
        ),
        Item(id=13, title="IPX7防水真无线耳机 运动无忧 智能触控 随时畅听高品质音乐"),
        Item(
            id=14, title="运动专用耳机 稳固佩戴 防汗设计 超长续航 低延迟音频 高清通话"
        ),
        Item(
            id=15,
            title="录音室级有线耳机 高清音质 舒适佩戴 可拆卸线材 多设备兼容 降噪麦克风",
        ),
    ]
)
print("Data inserted\n")


# Search data
print("=== SEARCH DATA ===")
results = (
    table.search("Bluetooth Headphones", search_type="fulltext").limit(3).to_list()
)
print(json.dumps(results, indent=2, ensure_ascii=False))


# Search data in other language
print("\n=== SEARCH DATA IN OTHER LANGUAGE ===")
results = table.search("蓝牙耳机", search_type="fulltext").limit(3).to_list()
print(json.dumps(results, indent=2, ensure_ascii=False))
