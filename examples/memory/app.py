import streamlit as st
from memory import init_clients, Memory, chat_with_memories

# Page config
st.set_page_config(
    page_title="Memory Chat",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize clients
@st.cache_resource(show_spinner="Initializing memory...")
def init_clients_cached():
    return init_clients()


openai_client, tidb_client, embedding_fn = init_clients_cached()


# Initialize memory
@st.cache_resource
def init_memory():
    return Memory(tidb_client, embedding_fn, openai_client)


memory = init_memory()

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"
if "chats" not in st.session_state:
    st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"
if "chat_counter" not in st.session_state:
    st.session_state.chat_counter = 1


# Helper functions for chat management
def create_new_chat():
    st.session_state.chat_counter += 1
    new_chat_name = f"Chat {st.session_state.chat_counter}"
    st.session_state.chats[new_chat_name] = []
    st.session_state.current_chat = new_chat_name
    st.rerun()


def delete_chat(chat_name):
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[chat_name]
        if st.session_state.current_chat == chat_name:
            st.session_state.current_chat = list(st.session_state.chats.keys())[0]
        st.rerun()


def switch_chat(chat_name):
    st.session_state.current_chat = chat_name
    st.rerun()


# Main UI

# Create two columns layout
col1, col2 = st.columns([2, 1])

with col1:
    # Chat container
    chat_container = st.container(border=False)

    with chat_container:
        # Display chat messages for current chat
        current_messages = st.session_state.chats[st.session_state.current_chat]
        for message in current_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        current_chat = st.session_state.chats[st.session_state.current_chat]
        if prompt := st.chat_input("Type your message here..."):
            # Add user message to current chat history
            current_chat.append({"role": "user", "content": prompt})

            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = chat_with_memories(
                        prompt, memory, openai_client, st.session_state.user_id
                    )
                    st.markdown(response)

            # Add assistant response to current chat history
            current_chat.append({"role": "assistant", "content": response})

with col2:
    st.markdown("#### Memories")

    # Display memories in a scrollable container
    try:
        memories = memory.get_all_memories(st.session_state.user_id)

        if memories:
            with st.container(height=500, border=False):
                for i, mem in enumerate(memories):
                    title = f"Memory#{i + 1} - {mem['created_at'].strftime('%Y-%m-%d %H:%M')}"
                    with st.expander(title, expanded=True):
                        st.write(mem["memory"])
                        st.caption(f"Created: {mem['created_at']}")
            st.markdown(f"Total Memories: {len(memories)}")
            # Add clear memories button
            if st.button("🗑️ Clear All Memories", use_container_width=True):
                try:
                    memory.table.truncate()
                    st.success("All memories cleared successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error clearing memories: {str(e)}")
        else:
            st.info(
                "Start chatting. The memory module will extract the key facts during the conversation and save them as memories automatically."
            )

    except Exception as e:
        st.error(f"Error loading memories: {str(e)}")


# Sidebar with settings
with st.sidebar:
    st.logo(
        "../assets/logo-full.svg", size="large", link="https://pingcap.github.io/ai/"
    )
    st.markdown("""**Memory** is a important component of intelligent agents that enables persistent storage 
and semantic retrieval of key information including user preferences, conversation context, 
and facts.
    """)

    st.markdown("##### User ID")
    user_id = st.text_input(
        "User ID", value=st.session_state.user_id, label_visibility="collapsed"
    )
    if user_id != st.session_state.user_id:
        st.session_state.user_id = user_id
        # Clear all chats when switching users
        st.session_state.chats = {"Chat 1": []}
        st.session_state.current_chat = "Chat 1"
        st.session_state.chat_counter = 1
        st.rerun()

    st.markdown("##### Chat List")

    # New chat button
    if st.button("➕ New Chat", use_container_width=True):
        create_new_chat()

    # Chat list
    for chat_name in st.session_state.chats.keys():
        if st.button(
            chat_name,
            key=f"chat_{chat_name}",
            use_container_width=True,
            type="primary"
            if chat_name == st.session_state.current_chat
            else "secondary",
        ):
            switch_chat(chat_name)
