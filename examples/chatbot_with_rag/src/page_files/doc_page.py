import streamlit as st
import json

from utils import list_file_names, delete_file, create_user

user_id = create_user(st.user.email)

st.title("Manage Uploaded Files")

def show_file_list(user_id: int):
    files_json = list_file_names(user_id)
    files_dict = json.loads(files_json)
    files = files_dict.get("files", [])

    if not files:
        st.info("No files uploaded yet.")
        return

    for file_name in files:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(file_name)
        with col2:
            if st.button("Delete", key=file_name):
                delete_file(user_id, file_name)
                st.success(f"Deleted '{file_name}'")
                st.rerun()

show_file_list(user_id)
