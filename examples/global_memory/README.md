# TiDB Memory Chatbot

A Streamlit-based chatbot with memory functionality that uses LiteLLM to interface with various LLM providers including AWS Bedrock, OpenAI, Anthropic Claude, and Google Gemini.

## Features

- **Session Management**: Create, manage, and close chat sessions
- **Memory System**: Toggle between memory ON/OFF modes
  - **Memory ON**: Previous session summaries are included in new sessions for continuity
  - **Memory OFF**: Each session starts fresh, but summaries are still generated and stored
- **Multi-Provider Support**: Works with OpenAI, Anthropic, AWS Bedrock, Google Gemini via LiteLLM
- **Persistent Storage**: Sessions and summaries are stored locally in JSON format
- **Session History**: Load and view previous sessions
- **Real-time Statistics**: View storage and usage statistics

## Setup

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and configure your API keys for your preferred LLM provider:

   ```env
   # For OpenAI
   OPENAI_API_KEY=your_openai_api_key_here
   DEFAULT_MODEL=gpt-3.5-turbo

   # For AWS Bedrock
   AWS_ACCESS_KEY_ID=your_aws_access_key_id
   AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
   AWS_REGION=us-east-1
   DEFAULT_MODEL=bedrock/anthropic.claude-v2

   # For Anthropic
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   DEFAULT_MODEL=claude-3-sonnet-20240229
   ```

3. **Run the application**:
   ```bash
   uv run python main.py
   ```

   Or directly with Streamlit:
   ```bash
   uv run streamlit run app.py
   ```

## Usage

### Basic Chat
1. Click "New Session" to start a conversation
2. Type your messages in the chat input
3. The AI will respond based on your configured model

### Memory Management
- **Memory ON**:
  - When you close a session, it generates a summary
  - When you create a new session, previous summaries are loaded as context
  - Enables continuity across sessions

- **Memory OFF**:
  - Still generates summaries when sessions close (for storage)
  - New sessions don't load previous summaries
  - Each session is independent

### Session Management
- **New Session**: Creates a fresh conversation
- **Close Session**: Ends current session and generates summary
- **Load Session**: Resume a previous session from history

## Architecture

### Core Components

- **`app.py`**: Main Streamlit application with UI
- **`models.py`**: Data structures (ChatSession, Message, SessionSummary)
- **`llm_service.py`**: LiteLLM integration and response generation
- **`session_manager.py`**: Session persistence and memory management

### Data Storage

Sessions and summaries are stored locally in JSON files:
- `./sessions/sessions.json`: Chat sessions with messages
- `./sessions/summaries.json`: Generated session summaries

## Supported LLM Providers

Thanks to LiteLLM, this chatbot supports:

- **OpenAI**: GPT-3.5, GPT-4, GPT-4-turbo
- **Anthropic**: Claude-3 (Haiku, Sonnet, Opus)
- **AWS Bedrock**: Claude, Llama, Cohere models
- **Google**: Gemini models
- **And many more via LiteLLM**

## Configuration Options

Environment variables in `.env`:

- `DEFAULT_MODEL`: The LLM model to use
- `SESSION_STORAGE_PATH`: Path for session storage (default: `./sessions`)
- `MEMORY_ENABLED`: Default memory setting (default: `true`)

## Development

The project uses:
- **Streamlit**: Web interface
- **LiteLLM**: LLM provider abstraction
- **boto3**: AWS SDK (for Bedrock)
- **python-dotenv**: Environment variable management

## Troubleshooting

1. **LLM Service Not Connected**: Check your API keys in `.env`
2. **Module Not Found**: Run `uv install` to install dependencies
3. **Permission Errors**: Ensure write permissions for session storage directory