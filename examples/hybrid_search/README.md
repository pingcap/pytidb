# Hybrid Search Demo

In this demo, we will show you how to use hybrid search to combine vector search and full-text search on a set of documents.

<p align="center">
    <img src="https://github.com/user-attachments/assets/8caf22dc-d01e-470f-a7be-4656ba3ce3b2" alt="hybrid search demo" width="754"/>
</p>

## Prerequisites

* Python 3.10+
* TiDB database instance (👉 [Create a free TiDB Serverless Cluster](https://tidbcloud.com/free-trial))
* OpenAI API key (Go to [OpenAI](https://platform.openai.com/api-keys) to get the API key)

> **Note**
> 
> Currently, full-text search is only available for the following product option and region:
>
> - TiDB Cloud Serverless: Frankfurt (eu-central-1), Singapore (ap-southeast-1)

## How to run

**Step 1**: Clone the repository

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/hybrid_search;
```

**Step 2**: Install the required packages and setup environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step 3**: Set up environment to connect to storage

If you are using TiDB Cloud, you can find the connection parameters in the [TiDB Cloud console](https://tidbcloud.com/).

```bash
cat > .env <<EOF
TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USERNAME=root
TIDB_PASSWORD=
TIDB_DATABASE=test
OPENAI_API_KEY=<your-openai-api-key>
EOF
```

**Step 4**: Run the demo

**Option 1**: Run the Streamlit app

If you want to check the demo with a web UI, you can run the following command:

```bash
streamlit run app.py
```

Open the browser and visit `http://localhost:8501`

**Option 2**: Run the demo script

If you want to check the demo with a script, you can run the following command:

```bash
python main.py
```

Expected output:

```
=== CONNECT TO TIDB ===
Connected to TiDB.

=== CREATE TABLE ===
Table created.

=== INSERT SAMPLE DATA ===
Inserted 3 rows.

=== PERFORM HYBRID SEARCH ===
Search results:
[
    {
        "_distance": 0.4740166257687124,
        "_match_score": 1.6804268,
        "_score": 0.03278688524590164,
        "id": 60013,
        "text": "TiDB is a distributed database that supports OLTP, OLAP, HTAP and AI workloads."
    },
    {
        "_distance": 0.6428459116216618,
        "_match_score": 0.78427225,
        "_score": 0.03200204813108039,
        "id": 60015,
        "text": "LlamaIndex is a Python library for building AI-powered applications."
    },
    {
        "_distance": 0.641581407158715,
        "_match_score": null,
        "_score": 0.016129032258064516,
        "id": 60014,
        "text": "PyTiDB is a Python library for developers to connect to TiDB."
    }
]
```

