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
    # モーダルを開く
    with st.form("url_settings_form"):
        st.subheader("URL Settings")

        # URL保存機能
        with st.spinner("Loading saved URLs..."):
            saved_urls = get_saved_url_names()
            selected_url_preset = st.selectbox(
                "Load Saved URLs",
                [""] + saved_urls,
                key="url_preset_input"
            )

        if selected_url_preset:
            with st.spinner("Loading URL configuration..."):
                urls = load_urls(selected_url_preset)
                if urls:
                    st.session_state.target_url = urls["target_url"]
                    st.session_state.proxy_url = urls["proxy_url"]

        # URL入力フィールド
        col1, col2 = st.columns([3, 1])
        with col1:
            url_save_name = st.text_input("Save URLs as", key="url_save_name")

        # Target URL
        target_url = st.text_input(
            "Target URL",
            value=st.session_state.target_url,
            key="target_url_input"
        )

        # Proxy settings
        proxy_url = st.text_input(
            "Proxy URL (Optional)",
            value=st.session_state.proxy_url,
            key="proxy_url_input"
        )

        if proxy_url and not is_valid_proxy_url(proxy_url):
            st.error("Invalid proxy URL format")

        # Form submit buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            submit = st.form_submit_button("Save Settings")
        with col2:
            save_preset = st.form_submit_button("Save as Preset")
        with col3:
            delete_preset = st.form_submit_button("Delete Preset")

        if submit:
            with st.spinner("Saving settings..."):
                st.session_state.target_url = target_url
                st.session_state.proxy_url = proxy_url
                save_last_used_urls(target_url, proxy_url)
                st.success("Settings saved")
                return True

        if save_preset and url_save_name:
            with st.spinner("Saving URL preset..."):
                save_urls(url_save_name, target_url, proxy_url)
                st.success(f"Saved as {url_save_name}")
                st.rerun()

        if delete_preset and selected_url_preset:
            with st.spinner("Deleting URL preset..."):
                delete_urls(selected_url_preset)
                st.success(f"Deleted {selected_url_preset}")

    return False

def initialize_session_state():
    defaults = {
        "proxy_url": "",
        "target_url": "",
        "question": "",
        "retrieval_mode": "hybrid",
        "semantic_ranker": False,
        "semantic_captions": False,
        "top": 3,
        "temperature": 0.3,
        "prompt_template": "",
        "exclude_category": "",
        "selected_data": "",
        "save_name": "",
        "form_submitted": False,
        "show_url_settings": False
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Load last used URLs
    if not st.session_state.target_url and not st.session_state.proxy_url:
        last_urls = load_last_used_urls()
        st.session_state.target_url = last_urls.get("target_url","")
        st.session_state.proxy_url = last_urls.get("proxy_url","")

def load_saved_data(name):
    if name:
        data = load_post_data(name)
        if data:
            print(f"Loading saved data: {data}")  # デバッグログ
            # Update question
            if "question" in data:
                st.session_state.question = data["question"]
                st.session_state.question_input = data["question"]  # 入力フィールドも更新

            # Update overrides
            if "overrides" in data:
                overrides = data["overrides"]
                st.session_state.retrieval_mode = overrides.get("retrieval_mode", "hybrid")
                st.session_state.retrieval_mode_input = overrides.get("retrieval_mode", "hybrid")

                st.session_state.semantic_ranker = overrides.get("semantic_ranker", False)
                st.session_state.semantic_ranker_input = overrides.get("semantic_ranker", False)

                st.session_state.semantic_captions = overrides.get("semantic_captions", False)
                st.session_state.semantic_captions_input = overrides.get("semantic_captions", False)

                st.session_state.top = overrides.get("top", 3)
                st.session_state.top_input = overrides.get("top", 3)

                st.session_state.temperature = overrides.get("temperature", 0.3)
                st.session_state.temperature_input = overrides.get("temperature", 0.3)

                st.session_state.prompt_template = overrides.get("prompt_template", "")
                st.session_state.prompt_template_input = overrides.get("prompt_template", "")

                st.session_state.exclude_category = overrides.get("exclude_category", "")
                st.session_state.exclude_category_input = overrides.get("exclude_category", "")
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
                current_data = {
                    "question": st.session_state.question_input,  # 入力フィールドから直接取得
                    "overrides": {
                        "retrieval_mode": st.session_state.retrieval_mode_input,
                        "semantic_ranker": st.session_state.semantic_ranker_input,
                        "semantic_captions": st.session_state.semantic_captions_input,
                        "top": st.session_state.top_input,
                        "temperature": st.session_state.temperature_input,
                        "prompt_template": st.session_state.prompt_template_input,
                        "exclude_category": st.session_state.exclude_category_input
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
        # Question input
        st.text_area(
            label="質問内容を入力してください",
            value=st.session_state.question,
            key="question_input",
            height=200
        )

        st.subheader("オーバーライド設定")
        st.selectbox(
            "検索モード",
            ["hybrid", "vectors", "text"],
            index=["hybrid", "vectors", "text"].index(st.session_state.retrieval_mode),
            key="retrieval_mode_input",
        )

        col_a, col_b = st.columns(2)
        with col_a:
            st.checkbox(
                "セマンティックランカー",
                value=st.session_state.semantic_ranker,
                key="semantic_ranker_input",
            )

            st.checkbox(
                "セマンティックキャプション",
                value=st.session_state.semantic_captions,
                key="semantic_captions_input",
            )

        with col_b:
            st.number_input(
                "上位結果数",
                min_value=1,
                max_value=50,
                value=st.session_state.top,
                key="top_input",
            )

            st.number_input(
                "温度パラメータ",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.temperature,
                step=0.1,
                key="temperature_input",
            )

        st.text_area(
            label="プロンプトテンプレート",
            value=st.session_state.prompt_template,
            key="prompt_template_input",
            height=100
        )

        st.text_input(
            "除外カテゴリー",
            value=st.session_state.exclude_category,
            key="exclude_category_input",
        )

        # リクエスト名入力フィールド（オプショナル）
        request_name = st.text_input(
            "リクエスト名（オプショナル）",
            value="",
            key="request_name_input",
            help="リクエストを識別するための名前を指定できます。空の場合は自動生成されます。"
        )

        # Update session state before sending request
        if st.button("リクエスト送信", type="primary"):
            if not st.session_state.question_input:
                st.error("質問を入力してください")
                return

            if not st.session_state.target_url:
                st.error("ターゲットURLを入力してください")
                return

            # Update session state
            st.session_state.question = st.session_state.question_input
            st.session_state.retrieval_mode = st.session_state.retrieval_mode_input
            st.session_state.semantic_ranker = st.session_state.semantic_ranker_input
            st.session_state.semantic_captions = st.session_state.semantic_captions_input
            st.session_state.top = st.session_state.top_input
            st.session_state.temperature = st.session_state.temperature_input
            st.session_state.prompt_template = st.session_state.prompt_template_input
            st.session_state.exclude_category = st.session_state.exclude_category_input

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