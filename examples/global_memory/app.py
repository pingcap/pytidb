import streamlit as st
from dotenv import load_dotenv
from models import AppState
from session_manager import SessionManager
from llm_service import LLMService
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="TiDB Memory Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_services():
    """Initialize LLM service and session manager"""
    if "llm_service" not in st.session_state:
        st.session_state.llm_service = LLMService()

    if "session_manager" not in st.session_state:
        st.session_state.session_manager = SessionManager(
            llm_service=st.session_state.llm_service
        )

    if "app_state" not in st.session_state:
        st.session_state.app_state = AppState()


def sidebar():
    """Render sidebar with session management"""
    st.sidebar.title("🤖 TiDB Memory Chatbot")

    # Memory toggle
    memory_enabled = st.sidebar.toggle(
        "Memory",
        value=st.session_state.app_state.memory_enabled,
        help="When ON: Previous session summaries are included in new sessions. When OFF: Each session starts fresh.",
    )

    if memory_enabled != st.session_state.app_state.memory_enabled:
        st.session_state.app_state.memory_enabled = memory_enabled
        st.rerun()

    st.sidebar.divider()

    # Session management
    st.sidebar.subheader("Session Management")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("New Session", type="primary", use_container_width=True):
            create_new_session()

    with col2:
        if st.button("Close Session", use_container_width=True):
            close_current_session()

    # Current session info
    if st.session_state.app_state.current_session:
        session = st.session_state.app_state.current_session
        st.sidebar.info(f"""
        **Current Session:** {session.session_id}
        **Started:** {session.start_time.strftime('%H:%M:%S')}
        **Messages:** {len(session.messages)}
        **Memory:** {'ON' if session.memory_enabled else 'OFF'}
        """)
    else:
        st.sidebar.warning("No active session")

    st.sidebar.divider()

    # Session history
    st.sidebar.subheader("Session History")
    session_history = st.session_state.session_manager.get_session_history()

    if session_history:
        selected_session = st.sidebar.selectbox(
            "Load Previous Session:",
            options=[""] + session_history,
            format_func=lambda x: "Select a session..." if x == "" else f"Session {x}",
        )

        if selected_session and selected_session != "":
            if st.sidebar.button("Load Session", use_container_width=True):
                load_session(selected_session)
    else:
        st.sidebar.text("No previous sessions")

    st.sidebar.divider()

    # Storage statistics
    if st.sidebar.button("Show Stats"):
        show_storage_stats()

    # Configuration status
    st.sidebar.subheader("Configuration")
    test_connection = st.session_state.llm_service.test_connection()
    if test_connection:
        st.sidebar.success("✅ LLM Service Connected")
    else:
        st.sidebar.error("❌ LLM Service Not Connected")
        st.sidebar.info("Check your .env file configuration")


def create_new_session():
    """Create a new chat session"""
    try:
        # Close current session if active
        if st.session_state.app_state.current_session:
            close_current_session()

        # Create new session
        new_session = st.session_state.session_manager.create_session(
            memory_enabled=st.session_state.app_state.memory_enabled
        )

        st.session_state.app_state.current_session = new_session

        # Clear chat history
        if "messages" in st.session_state:
            del st.session_state.messages

        st.success(f"New session {new_session.session_id} created!")
        st.rerun()

    except Exception as e:
        st.error(f"Error creating session: {str(e)}")
        logger.error(f"Error creating session: {str(e)}")


def close_current_session():
    """Close the current session"""
    if not st.session_state.app_state.current_session:
        st.warning("No active session to close")
        return

    try:
        session = st.session_state.app_state.current_session

        if len(session.messages) > 0:
            with st.spinner("Generating session summary..."):
                summary = st.session_state.session_manager.close_session(session)

                if summary:
                    st.success(f"Session {session.session_id} closed and summarized!")
                    with st.expander("Session Summary"):
                        st.write(summary.summary)
                else:
                    st.warning(
                        f"Session {session.session_id} closed but summary generation failed"
                    )
        else:
            st.info("Session closed (no messages to summarize)")

        # Clear current session
        st.session_state.app_state.current_session = None
        if "messages" in st.session_state:
            del st.session_state.messages

    except Exception as e:
        st.error(f"Error closing session: {str(e)}")
        logger.error(f"Error closing session: {str(e)}")


def load_session(session_id: str):
    """Load a previous session"""
    try:
        session = st.session_state.session_manager.load_session(session_id)

        if session:
            st.session_state.app_state.current_session = session

            # Load messages into Streamlit chat
            st.session_state.messages = []
            for message in session.messages:
                if message.role in ["user", "assistant"]:
                    st.session_state.messages.append(
                        {"role": message.role, "content": message.content}
                    )

            st.success(f"Session {session_id} loaded!")
            st.rerun()
        else:
            st.error(f"Could not load session {session_id}")

    except Exception as e:
        st.error(f"Error loading session: {str(e)}")
        logger.error(f"Error loading session: {str(e)}")


def show_storage_stats():
    """Show storage statistics"""
    try:
        stats = st.session_state.session_manager.get_storage_stats()

        with st.sidebar.expander("Storage Statistics", expanded=True):
            st.write(f"**Total Sessions:** {stats.get('total_sessions', 0)}")
            st.write(f"**Active Sessions:** {stats.get('active_sessions', 0)}")
            st.write(f"**Total Summaries:** {stats.get('total_summaries', 0)}")
            st.write(f"**Total Messages:** {stats.get('total_messages', 0)}")
            st.write(f"**Storage Path:** {stats.get('storage_path', 'Unknown')}")

    except Exception as e:
        st.sidebar.error(f"Error getting stats: {str(e)}")


def main():
    """Main application"""
    initialize_services()
    sidebar()

    # Main chat interface
    st.title("🤖 TiDB Memory Chatbot")

    # Check if we have an active session
    if not st.session_state.app_state.current_session:
        st.info("👈 Please create a new session to start chatting!")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button(
                "Create New Session", type="primary", use_container_width=True
            ):
                create_new_session()
        return

    # Initialize chat messages
    if "messages" not in st.session_state:
        st.session_state.messages = []

        # Show memory context if enabled
        current_session = st.session_state.app_state.current_session
        if current_session.memory_enabled and current_session.previous_summaries:
            with st.expander("📚 Memory Context (Previous Sessions)", expanded=False):
                for summary in current_session.previous_summaries:
                    st.write(f"**Session {summary.session_id}:** {summary.summary}")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("What would you like to talk about?"):
        current_session = st.session_state.app_state.current_session

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add user message to session
        current_session.add_message("user", prompt)

        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Get conversation history including memory context
                    conversation_history = current_session.get_conversation_history()

                    # Generate response
                    response = st.session_state.llm_service.generate_response_sync(
                        conversation_history
                    )

                    st.markdown(response)

                    # Add assistant message to chat history and session
                    st.session_state.messages.append(
                        {"role": "assistant", "content": response}
                    )
                    current_session.add_message("assistant", response)

                    # Save session
                    st.session_state.session_manager.save_session(current_session)

                except Exception as e:
                    error_msg = f"Error generating response: {str(e)}"
                    st.error(error_msg)
                    logger.error(error_msg)


if __name__ == "__main__":
    main()
