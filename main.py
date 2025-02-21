import streamlit as st
from utils.db_utils import init_db, initialize_session_state
import pages.home
import pages.request_management

def main():
    st.set_page_config(
        page_title="Proxy Web Request Manager",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize database and session state
    init_db()
    initialize_session_state()

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select Page",
        ["Home", "Request Management"],
        key="navigation"
    )

    # Page routing
    if page == "Home":
        pages.home.show()
    else:
        pages.request_management.show()

if __name__ == "__main__":
    main()
