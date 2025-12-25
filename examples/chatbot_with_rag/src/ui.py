import streamlit as st
import json
from utils import (
    upload_file, chat, create_session,
    show_all_sessions, show_history,
    add_message, delete_session,
)

def new_chat_page():
    """Page function for new chat"""
    st.header(f"Welcome, {st.session_state.get('user_name', 'User')}!")
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not found")
        return
        
    st.subheader("🆕 New Chat")
    st.info("💬 Enter your first question to start the chat.")

    user_input = st.chat_input("Type your first question here...")
    if user_input:
        try:
            session_id = create_session(user_id)
            session_id_str = str(session_id)

            # Initialize session state for new chat
            st.session_state.chats = st.session_state.get('chats', {})
            st.session_state.chat_names = st.session_state.get('chat_names', {})
            st.session_state.chat_order = st.session_state.get('chat_order', [])
            
            st.session_state.chats[session_id_str] = []
            st.session_state.chat_names[session_id_str] = "🕓 New Chat"
            st.session_state.chat_order.insert(0, session_id_str)

            user_msg = {"role": "user", "content": user_input}
            st.session_state.chats[session_id_str].append(user_msg)
            
            # Save user message to database
            add_message(session_id_str, json.dumps(user_msg))

            # Display user message
            with st.chat_message("user"):
                st.markdown(user_input)

            # Get and display assistant response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = chat(user_id=user_id, MAX_CONTEXT_CHUNKS=10, str=user_input)
                    response = str(response) if response else "I couldn't generate a response."
                    st.markdown(response)

            # Save assistant response
            assistant_msg = {"role": "assistant", "content": response}
            st.session_state.chats[session_id_str].append(assistant_msg)
            add_message(session_id_str, json.dumps(assistant_msg))

            # Update chat name and switch to existing chat view
            words = user_input.strip().split()
            new_name = " ".join(words[:5]) if words else "Untitled Chat"
            st.session_state.chat_names[session_id_str] = new_name
            st.session_state.current_chat = session_id_str
            st.rerun()
            
        except Exception as e:
            st.error(f"Failed to create new chat: {str(e)}")

def existing_chat_page():
    """Single page for all existing chats"""
    st.header(f"Welcome, {st.session_state.get('user_name', 'User')}!")
    
    chat_id = st.session_state.get('current_chat')
    if not chat_id:
        st.error("No chat selected")
        return
        
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("User not found")
        return
            
    if 'chats' not in st.session_state or chat_id not in st.session_state.chats:
        st.warning("Chat not found.")
        return

    st.subheader(st.session_state.chat_names.get(chat_id, f"Chat {str(chat_id)[:8]}"))

    # Display existing messages
    for msg in st.session_state.chats[chat_id]:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            with st.chat_message(msg["role"]):
                st.markdown(str(msg["content"]))
        else:
            st.warning("Found malformed message in chat history")

    user_input = st.chat_input("Type your message here...")

    if user_input:
        user_msg = {"role": "user", "content": user_input}
        st.session_state.chats[chat_id].append(user_msg)
        add_message(chat_id, json.dumps(user_msg))

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chat(user_id=user_id, MAX_CONTEXT_CHUNKS=10, str=user_input)
                response = str(response) if response else "I couldn't generate a response."
                st.markdown(response)

        # Save assistant response
        assistant_msg = {"role": "assistant", "content": response}
        st.session_state.chats[chat_id].append(assistant_msg)
        add_message(chat_id, json.dumps(assistant_msg))
        st.rerun()

def render_sidebar(user_id, user_name, user_email):
    """Render the shared sidebar with file upload and user info"""
    st.sidebar.title("🗂️ Chat Sessions")

    # File upload
    uploaded_global = st.sidebar.file_uploader("📂 Upload Personal Data (PDF)", type=["pdf"])
    if uploaded_global is not None:
        file_path = f"/tmp/{uploaded_global.name}"
        with open(file_path, "wb") as f:
            f.write(uploaded_global.read())

        upload_msg = upload_file(user_id = user_id, file=file_path)
        st.sidebar.success(upload_msg)

    # New chat button
    if st.sidebar.button("➕ New Chat"):
        st.session_state.current_chat = None
        st.rerun()

    # Show list of existing chats in sidebar
    if st.session_state.get('chats'):
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Your Chats:**")
        
        for chat_id in reversed(st.session_state.get('chat_order', [])[-10:]): # Show last 10 chats
            if chat_id in st.session_state.get('chats', {}):
                chat_name = st.session_state.chat_names.get(chat_id, f"Chat {chat_id[:8]}")
                display_name = chat_name[:25] + "..." if len(chat_name) > 25 else chat_name
                
                if st.sidebar.button(f"💬 {display_name}", key=f"nav_{chat_id}"):
                    st.session_state.current_chat = chat_id
                    st.rerun()
    
    # Delete current chat button
    if st.session_state.get('current_chat') and st.sidebar.button("🗑 Delete Current Chat"):
        current_chat_id = st.session_state.current_chat
        try:
            delete_session(current_chat_id)
            # Clean up session state
            if current_chat_id in st.session_state.chats:
                del st.session_state.chats[current_chat_id]
            if current_chat_id in st.session_state.chat_names:
                del st.session_state.chat_names[current_chat_id]
            if current_chat_id in st.session_state.chat_order:
                st.session_state.chat_order.remove(current_chat_id)
            
            st.session_state.current_chat = None
            st.sidebar.success("Chat deleted successfully!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Failed to delete chat: {str(e)}")

    # User info
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **{user_name}**")
    
    # Logout button
    if st.sidebar.button("🚪 Log out"):
        for key in list(st.session_state.keys()):
            if key not in ['user_id']:
                del st.session_state[key]
        st.logout()

def initialize_chat_state(user_id):
    """Initialize chat state and load existing chats"""
    try:
        all_session_ids = show_all_sessions(user_id)
    except Exception as e:
        st.error(f"Failed to load sessions: {str(e)}")
        all_session_ids = []

    # Initialize session state
    st.session_state.chats = st.session_state.get('chats', {})
    st.session_state.chat_names = st.session_state.get('chat_names', {})
    st.session_state.chat_order = st.session_state.get('chat_order', [])
    st.session_state.user_id = user_id

    # Load existing chats data into session state
    for session_id in all_session_ids:
        try:
            session_id_str = str(session_id)
            history_json = show_history(user_id, session_id)
            
            if history_json:
                history = json.loads(history_json)
                if not isinstance(history, list):
                    st.warning(f"Invalid history format for session {session_id_str}")
                    history = []
            else:
                history = []
                
            # Generate chat name from first user message
            chat_name = f"Chat {session_id_str[:8]}"
            for msg in history:
                if isinstance(msg, dict) and msg.get("role") == "user" and msg.get("content"):
                    content_words = msg["content"].split()[:5]
                    chat_name = " ".join(content_words) if content_words else chat_name
                    break

            # Store in session state
            st.session_state.chats[session_id_str] = history
            st.session_state.chat_names[session_id_str] = chat_name
            if session_id_str not in st.session_state.chat_order:
                st.session_state.chat_order.append(session_id_str)

        except Exception as e:
            st.warning(f"Error loading history for session {session_id}: {e}")

    # Render sidebar
    render_sidebar(user_id, st.session_state.user_name, st.session_state.user_email)
    
    # Determine which page to show
    if st.session_state.get('current_chat'):
        existing_chat_page()
    else:
        new_chat_page()
