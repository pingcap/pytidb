# Streamlit Examples

* Use autoflow as RAG framework
* Use Streamlit as web ui


## Prerequisites
* Python 3.8+
* OpenAI API key
* TiDB server connection string, either local or TiDB Cloud


## How to run

**Step0**: Clone the repo

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/;
```

**Step1**: Install the required packages

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step2**: Run the Streamlit app

```bash
streamlit run examples/text2sql/main.py
```

**Step3**: Open the browser and visit `http://localhost:8501`

* Input OpenAI API key in left sidebar
* Input the TiDB Cloud connection string in left sidebar, the format is `mysql+pymysql://root@localhost:4000/test`