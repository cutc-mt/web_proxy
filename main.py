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

    # シンプル化したサイドバーナビゲーション
    with st.sidebar:
        st.title("Web Request Manager")
        page = st.radio(
            "Menu",
            ["Request Form", "Request History"],
            key="navigation",
            label_visibility="collapsed"
        )

    # ページルーティング
    if page == "Request Form":
        pages.home.show()
    else:
        pages.request_management.show()

if __name__ == "__main__":
    main()