import streamlit as st

doc_page = st.Page("page_files/doc_page.py", title = "Manage Uploaded Files")
main_page = st.Page("page_files/main_page.py", title = "Chats")
login_page = st.Page("page_files/login_page.py")


def main():
    if not st.user.is_logged_in:
        pg = st.navigation([login_page])
    else:
        pg = st.navigation([main_page, doc_page])
    pg.run()

if __name__ == "__main__":
    main()
    
