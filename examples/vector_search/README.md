# Vector Search Examples

* Use `pytidb` to connect to TiDB
* Use `ollama` to deploy local embedding model
* Use Streamlit as web ui

<img width="1382" alt="Image" src="https://github.com/user-attachments/assets/f63302d7-6a79-44cf-b13a-610d7560be82" />

## Prerequisites
* Python 3.8+
* Ollama
* TiDB server connection string, either local or TiDB Cloud


## How to run

**Step0**: Install ollama and start embedding service

Follow the [installation docs](https://ollama.com/download) to install Ollama, then pull the embedding service like this:

```bash
ollama pull mxbai-embed-large
```

Test the embedding service to make sure it is running:

```bash
curl http://localhost:11434/api/embed -d '{
  "model": "mxbai-embed-large",
  "input": "Llamas are members of the camelid family"
}'
```

**Step1**: Clone the repo

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/vector_search/;
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
