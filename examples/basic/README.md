# Basic CRUD Demo

This example demonstrates basic CRUD (Create, Read, Update, Delete) operations with PyTiDB.

* Use `pytidb` to connect to TiDB
* Perform basic CRUD operations on data

## Prerequisites
* Python 3.8+
* TiDB server connection string (local or TiDB Cloud)

## How to run

**Step1**: Clone the repo

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/basic/
```

**Step2**: Install the required packages

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```


**Step3**: Set up environment to connect to storage

If you are using TiDB Cloud, you can find the connection parameters in the [TiDB Cloud console](https://tidbcloud.com/) and set up the environment variable like this:

```bash
cat > .env <<EOF
TIDB_HOST={gateway-region}.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USERNAME={prefix}.root
TIDB_PASSWORD={password}
TIDB_DATABASE=test
EOF
```

If you are using a local TiDB server, you can set up the environment variable like this:

```bash
cat > .env <<EOF
TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USERNAME=root
TIDB_PASSWORD=
TIDB_DATABASE=test
EOF
```

**Step4**: Run the demo

```bash
python main.py
```

*Expected output:*

```bash
Creating table...

=== CREATE ===
Created 3 items

=== READ ===
ID: 1, Name: First item, Description: This is item #1
ID: 2, Name: Second item, Description: This is item #2
ID: 3, Name: Third item, Description: This is item #3

=== UPDATE ===
Updated item with ID: 1
After update - ID: 1, Name: Updated item, Description: This item was updated

=== DELETE ===
Deleted item with ID: 2

=== FINAL STATE ===
ID: 1, Name: Updated item, Description: This item was updated
ID: 3, Name: Third item, Description: This is item #3

Basic CRUD operations completed!
```