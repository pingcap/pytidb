# Chatbot with RAG 

* An RAG-Driven AI Chatbot that allows users to manage a private knowledge base by feeding private files, therefore obtaining more accurate, reliable, and secure answers about any private fields that simple LLMs cannot answer
* Use `pytidb` to connect to TiDB
* Use `openai` to deploy embedding model and response generation
* Use Streamlit as web ui

## Prerequisites
* Python 3.10+
* A TiDB Cloud Serverless cluster: Create a free cluster here: tidbcloud.com
* OpenAI API key: Go to Open AI to get your own API key
* Google Auth: Create a web application in Google Cloud Console (https://docs.streamlit.io/develop/tutorials/authentication/google)

## How to run

**Step1**: Clone the repo

```bash
git clone https://github.com/pingcap/pytidb.git
cd examples/chatbot_with_rag
```

**Step2**: Install the required packages and setup environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Step3**: Set up environment to connect to storage

As you are using a local TiDB server, you can set up the environment variable like this:
(You can also referense)

```bash
cat > .env <<EOF
OPENAI_API_KEY=
TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USERNAME=root
TIDB_PASSWORD=
TIDB_DATABASE=test
EOF
```

**Step4**: Set up Google Auth Platform info

```bash
cat > .streamlit/secrets.toml <<EOF
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = 
client_id =
client_secret =
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
EOF
```

**Step5**: Run the Streamlit app

```bash
streamlit run src/app.py
```

**Step6**: open the browser and visit `http://localhost:8501`

