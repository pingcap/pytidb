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
cd pytidb/examples/embedding_search/;
```

**Step2**: Install the required packages and setup environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step3**: Run the Streamlit app

```bash
streamlit run main.py
```

**Step4**: open the browser and visit `http://localhost:8501`
