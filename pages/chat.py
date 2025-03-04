import streamlit as st
import json
import uuid
from utils.db_utils import (
    save_chat_settings,
    load_chat_settings,
    get_chat_settings_list,
    save_chat_thread,
    save_chat_message,
    load_chat_threads,
    load_chat_messages,
    delete_chat_thread
)
from utils.chat_backends.manager import ChatBackendManager
from datetime import datetime

def initialize_chat_state():
    """Initialize chat state"""
    if "chat_settings" not in st.session_state:
        backend_manager = ChatBackendManager()
        current_backend = backend_manager.get_current_backend()
        st.session_state.chat_settings = current_backend.get_settings_schema()
    
    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None
    
    if "current_backend_id" not in st.session_state:
        st.session_state.current_backend_id = "azure_openai_legacy"

def update_thread_order(thread_id: str):
    """Update thread's last modified time"""
    save_chat_thread(thread_id, get_thread_name(thread_id))
    st.rerun()

def get_thread_name(thread_id: str) -> str:
    """Get thread name"""
    threads = load_chat_threads()
    thread = next((t for t in threads if t["id"] == thread_id), None)
    return thread["name"] if thread else ""

def create_new_thread():
    """Create a new chat thread"""
    try:
        thread_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        name = f"新しい会話 ({timestamp})"
        save_chat_thread(thread_id, name)
        st.session_state.current_thread_id = thread_id
        st.rerun()
    except Exception as e:
        st.error(f"スレッドの作成に失敗しました: {str(e)}")

def delete_thread(thread_id: str):
    """Delete a chat thread"""
    try:
        delete_chat_thread(thread_id)
        st.session_state.current_thread_id = None
        st.rerun()
    except Exception as e:
        st.error(f"スレッドの削除に失敗しました: {str(e)}")

def get_thread_messages(thread_id: str):
    """Get thread messages"""
    return load_chat_messages(thread_id)

def handle_chat_interaction(prompt):
    """Handle chat interaction using the current backend"""
    if st.session_state.current_thread_id is None:
        st.error("スレッドが選択されていません")
        return

    thread_id = st.session_state.current_thread_id
    
    # Create user message
    user_message = {
        "role": "user",
        "content": prompt
    }
    
    # Get message history
    messages = get_thread_messages(thread_id)
    messages_with_new = messages + [user_message]
    
    try:
        # Get response from backend
        backend_manager = ChatBackendManager()
        current_backend = backend_manager.get_current_backend()
        
        with st.spinner("応答を生成中..."):
            response = current_backend.handle_chat(
                messages_with_new,
                st.session_state.chat_settings
            )
            
            if "message" in response:
                # Save messages
                save_chat_message(thread_id, "user", prompt)
                assistant_message = response["message"]
                save_chat_message(
                    thread_id,
                    "assistant",
                    assistant_message["content"],
                    response.get("context", {})
                )
                update_thread_order(thread_id)
                
                # Display response
                with st.chat_message("assistant"):
                    st.markdown(assistant_message["content"])
                    
                    # Display reference information and thoughts
                    context = response.get("context", {})
                    if "data_points" in context and context["data_points"]:
                        with st.expander("🔍 参照情報", expanded=False):
                            for idx, data_point in enumerate(context["data_points"], 1):
                                st.markdown(f"**{idx}.** {data_point}")
                                if idx < len(context["data_points"]):
                                    st.divider()

                    if "thoughts" in context:
                        with st.expander("💭 思考プロセス", expanded=False):
                            st.write(context["thoughts"])

                    # Display followup questions
                    if "followup_questions" in context and context["followup_questions"]:
                        st.markdown("**💭 関連する質問:**")
                        for question in context["followup_questions"]:
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                            if st.button(
                                question,
                                key=f"followup_{thread_id}_{hash(question)}_{timestamp}",
                                use_container_width=True
                            ):
                                handle_chat_interaction(question)
            
            elif "error" in response:
                st.error(f"エラー: {response['error']}")
    
    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")

def render_thread_sidebar():
    """Render thread management sidebar"""
    st.sidebar.title("💭 スレッド管理")
    
    if st.sidebar.button("➕ 新しい会話を開始"):
        create_new_thread()
    
    # Add scrollable container style
    st.markdown("""
        <style>
        div[data-testid="stSidebarContent"] div.stMarkdown + div[data-testid="stVerticalBlock"] {
            max-height: 300px;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Thread list
    st.sidebar.markdown("### 会話一覧")
    threads = load_chat_threads()
    with st.container():
        for thread in threads:
            col1, col2 = st.sidebar.columns([4, 1])
            with col1:
                if st.button(
                    thread["name"],
                    key=f"thread_{thread['id']}",
                    use_container_width=True,
                    type="primary" if thread["id"] == st.session_state.current_thread_id else "secondary"
                ):
                    st.session_state.current_thread_id = thread["id"]
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"delete_{thread['id']}", help="このスレッドを削除"):
                    delete_thread(thread["id"])

def render_settings_panel():
    """Render settings panel"""
    with st.sidebar.expander("⚙️ チャット設定", expanded=False):
        # Backend selection
        backend_manager = ChatBackendManager()
        backends = backend_manager.get_available_backends()
        backend_options = {
            backend_id: backend_cls().get_name()
            for backend_id, backend_cls in backends.items()
        }
        
        selected_backend = st.selectbox(
            "バックエンド",
            options=list(backend_options.keys()),
            format_func=lambda x: backend_options[x],
            index=list(backend_options.keys()).index(st.session_state.current_backend_id)
        )
        
        if selected_backend != st.session_state.current_backend_id:
            st.session_state.current_backend_id = selected_backend
            backend_manager.set_current_backend(selected_backend)
            st.session_state.chat_settings = backend_manager.get_current_backend().get_settings_schema()
            st.rerun()
        
        # Settings presets
        col1, col2 = st.columns(2)
        with col1:
            preset_name = st.text_input("プリセット名", key="preset_name", placeholder="新しいプリセット")
        with col2:
            if st.button("保存", key="save_preset", use_container_width=True):
                if preset_name:
                    save_chat_settings(preset_name, st.session_state.chat_settings)
                    st.success(f"プリセット '{preset_name}' を保存しました")
                else:
                    st.warning("プリセット名を入力してください")
        
        # Load preset
        presets = get_chat_settings_list()
        if presets:
            preset = st.selectbox(
                "プリセットを読み込む",
                options=[""] + [p["name"] for p in presets],
                format_func=lambda x: "プリセットを選択" if x == "" else x
            )
            if preset and st.button("読み込む", key="load_preset", use_container_width=True):
                settings = load_chat_settings(preset)
                if settings:
                    st.session_state.chat_settings.update(settings)
                    st.success(f"プリセット '{preset}' を読み込みました")
                    st.rerun()
        
        # Import/Export settings
        col1, col2 = st.columns(2)
        with col1:
            if st.button("設定をエクスポート", use_container_width=True):
                settings_json = json.dumps(st.session_state.chat_settings, ensure_ascii=False, indent=2)
                st.download_button(
                    "JSONとしてダウンロード",
                    settings_json,
                    file_name="chat_settings.json",
                    mime="application/json",
                    use_container_width=True
                )
        with col2:
            uploaded_file = st.file_uploader("設定をインポート", type=["json"], label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    imported_settings = json.load(uploaded_file)
                    st.session_state.chat_settings.update(imported_settings)
                    st.success("設定をインポートしました")
                    st.rerun()
                except Exception as e:
                    st.error(f"設定のインポートに失敗しました: {str(e)}")
        
        st.divider()
        
        # Backend-specific settings
        current_backend = backend_manager.get_current_backend()
        st.session_state.chat_settings = current_backend.render_settings(st.session_state.chat_settings)

def chat_page():
    """Main chat page"""
    st.title("💬 チャット")
    
    # Initialize state
    initialize_chat_state()
    
    # Render sidebar components
    render_thread_sidebar()
    render_settings_panel()
    
    # Main chat area
    if st.session_state.current_thread_id is not None:
        threads = load_chat_threads()
        current_thread = next(
            (thread for thread in threads 
             if thread["id"] == st.session_state.current_thread_id),
            None
        )
        
        if current_thread:
            # Editable thread title
            col1, col2 = st.columns([6, 1])
            with col1:
                new_title = st.text_input(
                    "スレッド名",
                    value=current_thread["name"],
                    key=f"title_{current_thread['id']}",
                    label_visibility="collapsed"
                )
                if new_title != current_thread["name"]:
                    try:
                        save_chat_thread(current_thread["id"], new_title)
                        st.rerun()
                    except Exception as e:
                        st.error(f"スレッド名の更新に失敗しました: {str(e)}")
            
            # Chat history
            thread_id = current_thread["id"]
            messages = get_thread_messages(thread_id)
            for i, message in enumerate(messages):
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    
                    # Display context for assistant messages
                    if message["role"] == "assistant" and message.get("context"):
                        context = message["context"]
                        if "data_points" in context and context["data_points"]:
                            with st.expander("🔍 参照情報", expanded=False):
                                for idx, data_point in enumerate(context["data_points"], 1):
                                    st.markdown(f"**{idx}.** {data_point}")
                                    if idx < len(context["data_points"]):
                                        st.divider()

                        if "thoughts" in context:
                            with st.expander("💭 思考プロセス", expanded=False):
                                st.write(context["thoughts"])

                        # Display followup questions for the latest message
                        if i == len(messages) - 1 and "followup_questions" in context and context["followup_questions"]:
                            st.markdown("**💭 関連する質問:**")
                            for question in context["followup_questions"]:
                                key = f"followup_{thread_id}_{hash(question)}"
                                if st.button(
                                    question,
                                    key=key,
                                    use_container_width=True
                                ):
                                    handle_chat_interaction(question)
                                    st.rerun()
            
            # User input
            if prompt := st.chat_input("メッセージを入力してください"):
                with st.chat_message("user"):
                    st.markdown(prompt)
                handle_chat_interaction(prompt)
    else:
        st.info("👈 サイドバーから新しい会話を開始するか、既存の会話を選択してください")