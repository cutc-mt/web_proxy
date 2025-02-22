import streamlit as st
from utils.db_utils import init_db, initialize_session_state
import pages.home
import pages.request_management

def main():
    st.set_page_config(
        page_title="Proxy Web Request Manager",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": None
        }
    )

    # Initialize database and session state
    init_db()
    initialize_session_state()

    # シンプル化したサイドバーナビゲーション
    with st.sidebar:
        st.title("🌐 Web Request")
        page = st.radio(
            "",  # ラベルを削除
            ["📝 Request", "📋 History"],
            key="navigation",
            format_func=lambda x: x.split(" ")[1]  # アイコンを除いたテキストのみ表示
        )

    # ページルーティング
    if page == "📝 Request":
        pages.home.show()
    else:
        pages.request_management.show()

if __name__ == "__main__":
    main()