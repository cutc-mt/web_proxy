import streamlit as st
from utils.db_utils import init_db, initialize_session_state
import pages.simple_qa
import pages.chat
import pages.settings

def main():
    st.set_page_config(
        page_title="AI Assistant",
        page_icon="🤖",
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

    # サイドバーナビゲーション
    with st.sidebar:
        st.title("🤖 AI Assistant")
        page = st.radio(
            "",  # ラベルを削除
            ["🤔 Simple Q&A", "💬 Chat", "⚙️ Settings"],
            key="navigation",
            format_func=lambda x: x.split(" ", 1)[1]  # アイコンを除いたテキストのみ表示
        )

    # ページルーティング
    if page == "🤔 Simple Q&A":
        pages.simple_qa.show()
    elif page == "💬 Chat":
        pages.chat.chat_page()
    else:
        pages.settings.show()

if __name__ == "__main__":
    main()