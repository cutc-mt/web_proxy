import streamlit as st
import json
import uuid
from utils.api_utils import make_request
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
from datetime import datetime

def initialize_chat_state():
    """チャットの状態を初期化"""
    # チャット設定の初期化
    if "chat_settings" not in st.session_state:
        st.session_state.chat_settings = {
            "prompt_template": "",
            "include_category": "",
            "exclude_category": "",
            "top": 3,
            "temperature": 0.7,
            "minimum_reranker_score": 0.0,
            "minimum_search_score": 0.0,
            "retrieval_mode": "hybrid",
            "semantic_ranker": True,
            "semantic_captions": True,
            "suggest_followup_questions": True,
            "use_oid_security_filter": False,
            "use_groups_security_filter": False,
            "vector_fields": ["embedding"],
            "use_gpt4v": False,
            "gpt4v_input": "text",
            "language": "ja"
        }
    
    # 現在のスレッドIDの初期化
    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = None

def update_thread_order(thread_id: str):
    """スレッドの最終更新時刻を更新"""
    save_chat_thread(thread_id, get_thread_name(thread_id))
    st.rerun()

def get_thread_name(thread_id: str) -> str:
    """スレッド名を取得"""
    threads = load_chat_threads()
    thread = next((t for t in threads if t["id"] == thread_id), None)
    return thread["name"] if thread else ""

def create_new_thread():
    """新しいスレッドを作成（データベース実装）"""
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
    """スレッドを削除（データベース実装）"""
    try:
        delete_chat_thread(thread_id)
        st.session_state.current_thread_id = None
        st.rerun()
    except Exception as e:
        st.error(f"スレッドの削除に失敗しました: {str(e)}")

def get_thread_messages(thread_id: str):
    """スレッドのメッセージ履歴を取得（データベース実装）"""
    return load_chat_messages(thread_id)

def handle_chat_interaction(prompt):
    """チャットのやり取りを処理"""
    if st.session_state.current_thread_id is None:
        st.error("スレッドが選択されていません")
        return

    thread_id = st.session_state.current_thread_id
    
    # ユーザーメッセージを作成
    user_message = {
        "role": "user",
        "content": prompt
    }
    
    # バックエンドに送信する全メッセージ履歴を取得
    messages = get_thread_messages(thread_id)
    
    # リクエストペイロードの作成
    payload = {
        "messages": messages + [user_message],
        "context": {
            "overrides": st.session_state.chat_settings
        },
        "session_state": st.session_state.get("current_session_state", "")
    }
    
    try:
        # バックエンドAPIにリクエストを送信
        with st.spinner("応答を生成中..."):
            response = make_request("POST", "/chat", json.dumps(payload))
            
            if response:
                if "error" in response:
                    st.error(f"エラー: {response['error']}")
                    return
                
                # セッションステートの更新
                if "session_state" in response:
                    st.session_state.current_session_state = response["session_state"]
                
                if "message" in response:
                    if "error" in response:
                        st.error(f"エラー: {response['error']}")
                        return
                    
                    if "message" in response and "context" in response:
                        # ユーザーメッセージとアシスタントメッセージを保存
                        save_chat_message(thread_id, "user", prompt)
                        assistant_message = response["message"]
                        save_chat_message(thread_id, "assistant", assistant_message["content"], response["context"])
                        update_thread_order(thread_id)
                        
                        context = response["context"]
                        
                        # メッセージ表示
                        with st.chat_message("assistant"):
                            # メインの応答
                            st.markdown(assistant_message["content"])
                            
                            # 詳細情報
                            if "data_points" in context and context["data_points"]:
                                with st.expander("🔍 参照情報", expanded=False):
                                    st.markdown("**参照されたドキュメント:**")
                                    for idx, data_point in enumerate(context["data_points"], 1):
                                        st.markdown(f"{idx}. {data_point}")
                            
                            # 最新のメッセージの場合のみフォローアップ質問を表示
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
            else:
                st.error("応答の取得に失敗しました")
    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")

def render_thread_sidebar():
    """スレッド管理サイドバーの表示"""
    st.sidebar.title("💭 スレッド管理")
    
    # 新規スレッド作成ボタン
    if st.sidebar.button("➕ 新しい会話を開始"):
        create_new_thread()
    
    # スクロール可能なコンテナのスタイルを追加
    st.markdown("""
        <style>
        div[data-testid="stSidebarContent"] div.stMarkdown + div[data-testid="stVerticalBlock"] {
            max-height: 300px;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # スレッド一覧
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
    """設定パネルの表示"""
    with st.sidebar.expander("⚙️ チャット設定", expanded=False):
        # 設定プリセット管理
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

        # プリセットの読み込み
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

        # 設定のインポート/エクスポート
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
        
        # 基本設定
        st.session_state.chat_settings["prompt_template"] = st.text_area(
            "プロンプトテンプレート", 
            st.session_state.chat_settings["prompt_template"]
        )
        
        # 検索設定
        st.session_state.chat_settings["retrieval_mode"] = st.selectbox(
            "検索モード",
            ["hybrid", "text", "vectors"],
            index=["hybrid", "text", "vectors"].index(st.session_state.chat_settings["retrieval_mode"])
        )
        
        st.session_state.chat_settings["top"] = st.number_input(
            "取得件数",
            min_value=1,
            max_value=10,
            value=st.session_state.chat_settings["top"]
        )
        
        # スコア設定
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.chat_settings["minimum_reranker_score"] = st.number_input(
                "最小リランカースコア",
                min_value=0.0,
                max_value=1.0,
                value=float(st.session_state.chat_settings["minimum_reranker_score"])
            )
        with col2:
            st.session_state.chat_settings["minimum_search_score"] = st.number_input(
                "最小検索スコア",
                min_value=0.0,
                max_value=1.0,
                value=float(st.session_state.chat_settings["minimum_search_score"])
            )
        
        # 機能設定
        st.session_state.chat_settings["temperature"] = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.chat_settings["temperature"]),
            step=0.1,
            help="生成される応答のランダム性を制御します。高いほど創造的で、低いほど一貫した応答になります。"
        )
        
        st.session_state.chat_settings["semantic_ranker"] = st.checkbox(
            "セマンティックランカーを使用",
            st.session_state.chat_settings["semantic_ranker"]
        )
        st.session_state.chat_settings["semantic_captions"] = st.checkbox(
            "セマンティックキャプションを使用",
            st.session_state.chat_settings["semantic_captions"]
        )
        st.session_state.chat_settings["suggest_followup_questions"] = st.checkbox(
            "フォローアップ質問を提案",
            st.session_state.chat_settings["suggest_followup_questions"]
        )

def chat_page():
    """チャットページのメイン関数"""
    st.title("💬 チャット")
    
    # 状態の初期化
    initialize_chat_state()
    
    # サイドバーのスレッド管理
    render_thread_sidebar()
    
    # サイドバーの設定パネル
    render_settings_panel()
    
    # メインチャットエリア
    if st.session_state.current_thread_id is not None:
        threads = load_chat_threads()
        current_thread = next(
            (thread for thread in threads 
             if thread["id"] == st.session_state.current_thread_id),
            None
        )
        
        if current_thread:
            # スレッド名を編集可能に表示
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
            
            # チャット履歴の表示
            thread_id = current_thread["id"]
            messages = get_thread_messages(thread_id)
            for i, message in enumerate(messages):
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    
                    # アシスタントの応答の場合、コンテキスト情報を表示
                    if message["role"] == "assistant" and message.get("context"):
                        context = message["context"]
                        # データポイントの表示
                        if "data_points" in context and context["data_points"]:
                            with st.expander("🔍 参照情報", expanded=False):
                                st.markdown("**参照されたドキュメント:**")
                                for idx, data_point in enumerate(context["data_points"], 1):
                                    st.markdown(f"{idx}. {data_point}")
                        
                        # 最新のメッセージの場合のみフォローアップ質問を表示
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

            # ユーザー入力
            if prompt := st.chat_input("メッセージを入力してください"):
                with st.chat_message("user"):
                    st.markdown(prompt)
                handle_chat_interaction(prompt)
    else:
        # スレッドが選択されていない場合
        st.info("👈 サイドバーから新しい会話を開始するか、既存の会話を選択してください")