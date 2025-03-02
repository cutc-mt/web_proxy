import streamlit as st
import json
from utils.api_utils import send_request, is_valid_proxy_url, create_json_data, display_response
from utils.db_utils import (
    save_post_data, load_post_data, delete_post_data, save_request,
    get_saved_post_data_names, save_urls, load_urls, delete_urls,
    get_saved_url_names, save_last_used_urls, load_last_used_urls,
    get_all_post_data, import_post_data
)

def show_url_settings():
    """URL設定フォームを表示して処理する"""
    """URL設定フォームを表示し、設定を管理する"""
    st.subheader("URL設定")

    # 保存済みURLの選択（フォームの外で処理）
    saved_urls = get_saved_url_names()
    selected_url_preset = st.selectbox(
        "保存済みURLを読み込む",
        [""] + saved_urls,
        key="url_preset_input"
    )

    # プリセット選択時の処理
    if selected_url_preset:
        if selected_url_preset != st.session_state.get("last_loaded_preset"):
            with st.spinner("URL設定を読み込み中..."):
                urls = load_urls(selected_url_preset)
                if urls:
                    st.session_state.target_url = urls["target_url"]
                    st.session_state.proxy_url = urls["proxy_url"]
                    st.session_state.last_loaded_preset = selected_url_preset
                    st.success(f"プリセット「{selected_url_preset}」を読み込みました")
                    st.rerun()

    # フォームを開く
    with st.form("url_settings_form", clear_on_submit=False):
        st.subheader("URL入力")

        # URLの初期値を設定
        initial_target_url = st.session_state.get("target_url", "")
        initial_proxy_url = st.session_state.get("proxy_url", "")

        # プリセット保存用の名前入力
        url_save_name = st.text_input(
            "設定の保存名",
            value="",
            key="url_save_name",
            help="プリセットとして保存する場合の名前を入力してください"
        )

        # Target URLの入力フィールド
        target_url = st.text_input(
            "ターゲットURL",
            value=initial_target_url,
            key="target_url_input",
            help="APIのエンドポイントURLを入力してください",
            placeholder="https://api.example.com"
        )

        # Proxy URLの入力フィールド
        proxy_url = st.text_input(
            "プロキシURL（オプション）",
            value=initial_proxy_url,
            key="proxy_url_input",
            help="プロキシが必要な場合はURLを入力してください",
            placeholder="http://proxy.example.com"
        )

        # プロキシURLの形式チェック
        if proxy_url:
            if not is_valid_proxy_url(proxy_url):
                st.error("プロキシURLの形式が正しくありません")
                valid_proxy = False
            else:
                valid_proxy = True
        else:
            valid_proxy = True

        # 中央寄せのサブミットボタン
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                "設定を保存",
                type="primary",
                use_container_width=True
            )

        # フォーム送信時の処理
        if submitted:
            # バリデーションチェック
            if not target_url and not proxy_url:
                st.warning("保存するURLが入力されていません")
                return False
            
            if proxy_url and not valid_proxy:
                st.error("プロキシURLの形式が正しくないため、保存できません")
                return False

            # 設定の保存
            with st.spinner("URL設定を保存中..."):
                st.session_state.target_url = target_url
                st.session_state.proxy_url = proxy_url
                save_last_used_urls(target_url, proxy_url)

                # プリセットとして保存（名前が入力されている場合）
                if url_save_name:
                    save_urls(url_save_name, target_url, proxy_url)
                    st.success(f"プリセット「{url_save_name}」として保存しました")
                else:
                    st.success("URL設定を保存しました")
                return True

    return False

    # プリセットの削除ボタン（フォームの外に配置）
    if selected_url_preset:
        if st.button("選択したプリセットを削除", type="secondary"):
            with st.spinner("URLプリセットを削除中..."):
                delete_urls(selected_url_preset)
                st.success(f"プリセット「{selected_url_preset}」を削除しました")
                st.session_state.pop("last_loaded_preset", None)
                st.rerun()
def initialize_session_state():
    """UIの状態を初期化する

    注意:
        この関数はページの表示時に呼び出されます。
        ウィジェットのデフォルト値との競合に注意が必要です。
    """
    # 純粋なUI状態のみを初期化
    ui_states = {
        "question": "",
        "prompt_template": "",
        "exclude_category": "",
        "selected_data": "",
        "save_name": "",
        "form_submitted": False,
        "show_url_settings": False
    }

    # UIの状態のみを初期化
    for key, value in ui_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # URLの読み込みはdb_utils.initialize_session_stateで管理
    # URLの読み込みはdb_utils.initialize_session_stateに移動済み

def get_widget_key(base_name):
    """ウィジェットのキーを生成する
    
    保存されたデータのロード時に新しいキーを生成することで、
    ウィジェットの再作成を強制し、セッション状態との競合を防ぐ。
    """
    load_count = st.session_state.get("load_count", 0)
    return f"{base_name}_{load_count}"

def load_saved_data(name):
    if name:
        data = load_post_data(name)
        if data:
            # ロードカウントをインクリメント
            st.session_state.load_count = st.session_state.get("load_count", 0) + 1
            
            # 保存されたデータをセッション状態に保存
            if "question" in data:
                st.session_state[f"saved_question_{st.session_state.load_count}"] = data["question"]

            if "overrides" in data:
                overrides = data["overrides"]
                st.session_state[f"saved_retrieval_mode_{st.session_state.load_count}"] = overrides.get("retrieval_mode", "hybrid")
                st.session_state[f"saved_semantic_ranker_{st.session_state.load_count}"] = overrides.get("semantic_ranker", False)
                st.session_state[f"saved_semantic_captions_{st.session_state.load_count}"] = overrides.get("semantic_captions", False)
                st.session_state[f"saved_top_{st.session_state.load_count}"] = overrides.get("top", 3)
                st.session_state[f"saved_temperature_{st.session_state.load_count}"] = overrides.get("temperature", 0.3)
                st.session_state[f"saved_prompt_template_{st.session_state.load_count}"] = overrides.get("prompt_template", "")
                st.session_state[f"saved_exclude_category_{st.session_state.load_count}"] = overrides.get("exclude_category", "")
            st.rerun()  # ページを再読み込みしてウィジェットを更新
            return True
    return False

def reset_form():
    # Reset only specific form fields to default values
    defaults = {
        "selected_data": "",
        "save_name": "",
        "form_submitted": True  # フォーム送信フラグを設定
    }

    for key, value in defaults.items():
        st.session_state[key] = value

def show():
    st.title("Webリクエストマネージャー")

    # Initialize session state
    initialize_session_state()

    # URL Settings Button in the header
    if st.button("⚙️ URL設定"):
        st.session_state.show_url_settings = True

    # Show URL Settings Modal
    if st.session_state.show_url_settings:
        if show_url_settings():
            st.session_state.show_url_settings = False
            st.rerun()

    # Main content
    st.header("リクエスト入力")

    # POST data input
    col1, col2 = st.columns([2, 1])

    with col2:
        st.subheader("保存済みPOSTデータ")
        saved_data = get_saved_post_data_names()

        # Selectbox for loading saved data
        selected_data = st.selectbox(
            "Load Saved Data",
            [""] + saved_data,
            key="selected_data_input"
        )

        # Load data when selection changes
        if selected_data != st.session_state.selected_data:
            st.session_state.selected_data = selected_data
            if selected_data:
                load_saved_data(selected_data)
                st.rerun()

        # フォームが送信された後は空の値を表示
        initial_value = "" if st.session_state.form_submitted else st.session_state.get("save_name_input", "")
        save_name = st.text_input("Save as", value=initial_value, key="save_name_input")
        if st.button("保存"):
            if save_name:
                # 現在のウィジェットキーを使用してデータを取得
                current_load = st.session_state.get("load_count", 0)
                current_data = {
                    "question": st.session_state[get_widget_key("question")],
                    "overrides": {
                        "retrieval_mode": st.session_state[get_widget_key("retrieval_mode")],
                        "semantic_ranker": st.session_state[get_widget_key("semantic_ranker")],
                        "semantic_captions": st.session_state[get_widget_key("semantic_captions")],
                        "top": st.session_state[get_widget_key("top")],
                        "temperature": st.session_state[get_widget_key("temperature")],
                        "prompt_template": st.session_state[get_widget_key("prompt_template")],
                        "exclude_category": st.session_state[get_widget_key("exclude_category")]
                    }
                }
                save_post_data(save_name, current_data)
                st.success(f"{save_name}として保存しました")
                reset_form()  # 保存時のみフォームをリセット
                st.rerun()
            else:
                st.error("保存名を入力してください")

        if st.button("選択したデータを削除"):
            if selected_data:
                delete_post_data(selected_data)
                st.success(f"{selected_data}を削除しました")
                st.session_state.selected_data = ""
                st.rerun()

        # Export/Import buttons
        st.subheader("データのエクスポート/インポート")

        # エクスポートボタン
        if st.button("POSTデータをエクスポート"):
            with st.spinner("POSTデータをエクスポート中..."):
                # Get all saved POST data
                all_data = get_all_post_data()

                if all_data:
                    # Convert to JSON
                    json_str = json.dumps(all_data, ensure_ascii=False, indent=2)

                    # Create download button
                    st.download_button(
                        label="JSONファイルをダウンロード",
                        data=json_str,
                        file_name="post_data_export.json",
                        mime="application/json"
                    )
                else:
                    st.warning("エクスポートできるPOSTデータがありません")

        # インポート機能
        uploaded_file = st.file_uploader(
            "JSONファイルをインポート",
            type=["json"],
            help="エクスポートされたPOSTデータのJSONファイルを選択してください"
        )
        if uploaded_file is not None:
            try:
                import_data = json.load(uploaded_file)

                if st.button("インポートを実行"):
                    with st.spinner("POSTデータをインポート中..."):
                        success, errors = import_post_data(import_data)

                        if success > 0:
                            st.success(f"{success}件のデータをインポートしました")
                        if errors > 0:
                            st.error(f"{errors}件のデータをインポートできませんでした")

                        # Refresh the page to show new data
                        st.rerun()

            except Exception as e:
                st.error("JSONファイルの読み込みに失敗しました")
                st.error(f"エラー: {str(e)}")


    with col1:
        # 現在のロードカウントを取得
        current_load = st.session_state.get("load_count", 0)

        # Question input
        st.text_area(
            label="質問内容を入力してください",
            value=st.session_state.get(f"saved_question_{current_load}", ""),
            key=get_widget_key("question"),
            height=200
        )

        st.subheader("オーバーライド設定")
        # デフォルト値を直接指定し、インデックスの計算を避ける
        st.selectbox(
            "検索モード",
            ["hybrid", "vectors", "text"],
            index=["hybrid", "vectors", "text"].index(
                st.session_state.get(f"saved_retrieval_mode_{current_load}", "hybrid")
            ),
            key=get_widget_key("retrieval_mode")
        )

        col_a, col_b = st.columns(2)
        with col_a:
            st.checkbox(
                "セマンティックランカー",
                value=st.session_state.get(f"saved_semantic_ranker_{current_load}", False),
                key=get_widget_key("semantic_ranker")
            )

            st.checkbox(
                "セマンティックキャプション",
                value=st.session_state.get(f"saved_semantic_captions_{current_load}", False),
                key=get_widget_key("semantic_captions")
            )

        with col_b:
            st.number_input(
                "上位結果数",
                min_value=1,
                max_value=50,
                value=st.session_state.get(f"saved_top_{current_load}", 3),
                key=get_widget_key("top")
            )

            st.number_input(
                "温度パラメータ",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.get(f"saved_temperature_{current_load}", 0.3),
                step=0.1,
                key=get_widget_key("temperature")
            )

        st.text_area(
            label="プロンプトテンプレート",
            value=st.session_state.get(f"saved_prompt_template_{current_load}", ""),
            key=get_widget_key("prompt_template"),
            height=100
        )

        st.text_input(
            "除外カテゴリー",
            value=st.session_state.get(f"saved_exclude_category_{current_load}", ""),
            key=get_widget_key("exclude_category")
        )

        # リクエスト名入力フィールド（オプショナル）
        request_name = st.text_input(
            "リクエスト名（オプショナル）",
            value="",
            key="request_name_input",
            help="リクエストを識別するための名前を指定できます。空の場合は自動生成されます。"
        )

        # リクエスト送信処理
        if st.button("リクエスト送信", type="primary"):
            # 現在のウィジェットキーを取得
            current_question_key = get_widget_key("question")
            
            if not st.session_state.get(current_question_key):
                st.error("質問を入力してください")
                return

            if not st.session_state.target_url:
                st.error("ターゲットURLを入力してください")
                return

            # ウィジェットの値を直接使用してリクエストを作成
            post_data = create_json_data()

            # Create and send request
            post_data = create_json_data()
            response = send_request(
                st.session_state.target_url,
                post_data,
                st.session_state.proxy_url if st.session_state.proxy_url else None
            )

            if response:
                # Save request to database with optional request name
                save_request(
                    target_url=st.session_state.target_url,
                    post_data=json.dumps(post_data),
                    response=json.dumps(response) if isinstance(response, dict) else response,
                    proxy_url=st.session_state.proxy_url,
                    request_name=request_name if request_name else None
                )
                # Save response to session state for display
                st.session_state.last_response = response
                # Display the response
                display_response(response)