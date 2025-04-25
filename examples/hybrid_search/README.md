# Fulltext Search Examples

* Use `pytidb` to connect to TiDB
* Use Streamlit as web ui

## Prerequisites

* Python 3.10+
* TiDB database connection string (Only for TiDB Serverless `Frankfurt (eu-central-1)` region for now)
* OpenAI API key (Go to [OpenAI](https://platform.openai.com/api-keys) to get the API key)
* Jina AI API key (Go to [Jina AI](https://jina.ai/reranker) to get the API key)


## How to run

**Step1**: Clone the repository

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/hybrid_search;
```

**Step2**: Install the required packages and setup environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step3**: Set up environment to connect to storage

If you are using TiDB Cloud, you can find the connection string in the [TiDB Cloud console](https://tidbcloud.com/).


```bash
cat > .env <<EOF
TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USERNAME=root
TIDB_PASSWORD=
TIDB_DATABASE=test
OPENAI_API_KEY=<your-openai-api-key>
JINA_AI_API_KEY=<your-jina-ai-api-key>
EOF
```

**Step4**: Run the Streamlit app

```bash
streamlit run main.py
```

**Step5**: open the browser and visit `http://localhost:8501`
