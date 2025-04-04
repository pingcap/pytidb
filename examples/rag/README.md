# Vector Search Examples

* Use `pytidb` to connect to TiDB
* Use `ollama` to deploy local embedding model
* Use Streamlit as web ui


## Prerequisites
* Python 3.8+
* Ollama
* TiDB server connection string, either local or TiDB Cloud


## How to run

**Step0**: Install ollama and start embedding service

Follow the [installation docs](https://ollama.com/download) to install Ollama, then pull the embedding service and llm model like this:

```bash
ollama pull mxbai-embed-large
ollama pull ollama/llama3.2:3b
ollama run llama3.2:3b
```

Test the embedding service and llm model to make sure they are running:

```bash
curl http://localhost:11434/api/embed -d '{
  "model": "mxbai-embed-large",
  "input": "Llamas are members of the camelid family"
}'

curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "Hello, Who are you?"
}'
```

**Step1**: Clone the repo

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/rag/;
```

**Step2**: Install the required packages and setup environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step3**: Set up environment to connect to storage
If you are using TiDB Cloud, you'd better set up the environment variable `DATABASE_URL` to connect to the TiDB Cloud database. You can find the connection string in the [TiDB Cloud console](https://tidbcloud.com/).

```bash
cat > .env <<EOF
DATABASE_URL="mysql+pymysql://<username>:<password>@<host>:4000/test?ssl_verify_cert=true&ssl_verify_identity=true"
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

**Step4**: Run the Streamlit app

```bash
streamlit run main.py
```

**Step5**: open the browser and visit `http://localhost:8501`
