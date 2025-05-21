# Fulltext Search Examples

* Use `pytidb` to connect to TiDB
* Use Streamlit as web UI

## Prerequisites

* Python 3.10+
* TiDB server connection string


## How to run

**Step1**: Clone the repo

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/fulltext_search/;
```

**Step2**: Install the required packages and setup environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step3**: Set up environment to connect to database

Go to the [TiDB Cloud console](https://tidbcloud.com/), create a new cluster if you don't have one, and then get the connection parameters on the connection dialog.

```bash
cat > .env <<EOF
TIDB_HOST={gateway-region}.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USERNAME={prefix}.root
TIDB_PASSWORD={password}
TIDB_DATABASE=test
EOF
```

**Step4**: Run the Streamlit app

```bash
streamlit run main.py
```

**Step5**: open the browser and visit `http://localhost:8501`
