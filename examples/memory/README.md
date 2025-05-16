# Agent Memory Examples

* Use `pytidb` to connect to TiDB

## Prerequisites

* Python 3.10+
* TiDB server connection parameters, either local or TiDB Cloud
* OpenAI API key


## How to run

**Step1**: Clone the repo

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/memory;
```

**Step2**: Install the required packages and setup environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step3**: Set up environment to connect to storage

You can find the connection string in the [TiDB Cloud console](https://tidbcloud.com/).

If you are using a local TiDB server, you can set up the environment variable like this:

```bash
cat > .env <<EOF
TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USERNAME=root
TIDB_PASSWORD=
TIDB_DATABASE=test

OPENAI_API_KEY=your_openai_api_key
EOF
```

**Step4**: Run the app

```bash
python main.py
```
