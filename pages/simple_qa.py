import streamlit as st
import pandas as pd
import json
from utils.enhance_prompt import refine_query
from utils.db_utils import (
    load_requests_summary, delete_request, update_request_memo, save_request,
    save_post_data, load_post_data, get_saved_post_data_names,
    get_all_post_data, import_post_data, delete_post_data
)
from utils.api_utils import make_request
from datetime import datetime
# 詳細設定を表示するフラグメント関数

def show_detail_settings():
    """詳細設定部分を表示"""
    col1, col2 = st.columns(2)
    with col1:
        modes = ["hybrid", "vectors", "text"]
        st.selectbox(
            "検索モード",
            modes,
            key="_retrieval_mode",
            index=modes.index(st.session_state.get("retrieval_mode", "hybrid"))
        )
        
        st.number_input(
            "参照件数",
            min_value=1,
            max_value=50,
            key="_top",
            value=st.session_state.get("top", 3)
        )

    with col2:
        st.checkbox(
            "セマンティック検索",
            key="_semantic_ranker",
            value=st.session_state.get("semantic_ranker", True)
        )
        
        st.checkbox(
            "セマンティックキャプション",
            key="_semantic_captions",
            value=st.session_state.get("semantic_captions", False)
        )

    # 生成設定
    st.subheader("生成設定")
    st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        step=0.1,
        key="_temperature",
        value=st.session_state.get("temperature", 0.3)
    )

    st.text_area(
        "除外カテゴリ（カンマ区切り）",
        key="_exclude_category",
        value=st.session_state.get("exclude_category", "")
    )

    st.text_area(
        "プロンプトテンプレート",
        key="_prompt_template",
        value=st.session_state.get("prompt_template", "")
    )

    # 一時的な設定値を取得
    current_settings = {
        "retrieval_mode": st.session_state.get("_retrieval_mode"),
        "top": st.session_state.get("_top"),
        "semantic_ranker": st.session_state.get("_semantic_ranker"),
        "semantic_captions": st.session_state.get("_semantic_captions"),
        "temperature": st.session_state.get("_temperature"),
        "exclude_category": st.session_state.get("_exclude_category"),
        "prompt_template": st.session_state.get("_prompt_template")
    }

    # デフォルト値で補完
    defaults = {
        "retrieval_mode": "hybrid",
        "top": 3,
        "semantic_ranker": True,
        "semantic_captions": False,
        "temperature": 0.3,
        "exclude_category": "",
        "prompt_template": ""
    }

    return {key: current_settings.get(key, defaults[key]) for key in defaults.keys()}

def sync_settings():
    """現在の設定値を取得して同期"""
    settings = {
        "retrieval_mode": st.session_state.get("retrieval_mode", "hybrid"),
        "top": st.session_state.get("top", 3),
        "semantic_ranker": st.session_state.get("semantic_ranker", True),
        "semantic_captions": st.session_state.get("semantic_captions", False),
        "temperature": st.session_state.get("temperature", 0.3),
        "exclude_category": st.session_state.get("exclude_category", ""),
        "prompt_template": st.session_state.get("prompt_template", "")
    }
    return settings

def initialize_qa_state():
    """Simple Q&Aのセッション状態を初期化"""
    # 一時的な質問がある場合は保持
    next_question = st.session_state.pop("_next_question", None)
    
    # デフォルト値
    defaults = {
        "detail_settings_expanded": False,
        "history_expanded": False,
        "retrieval_mode": "hybrid",
        "top": 3,
        "semantic_ranker": True,
        "semantic_captions": False,
        "temperature": 0.3,
        "exclude_category": "",
        "prompt_template": ""
    }
    
    # 存在しないキーのみ初期化
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    # タブの状態を初期化
    if "active_settings_tab" not in st.session_state:
        st.session_state["active_settings_tab"] = 0
    
    # 一時的な状態がある場合は反映
    if "_temp_state" in st.session_state:
        temp_state = st.session_state.pop("_temp_state")
        
        # 設定を復元
        if "settings" in temp_state:
            for key, value in temp_state["settings"].items():
                if value is not None:
                    st.session_state[key] = value
        
        # 改善された質問を設定
        if "enhanced_question" in temp_state:
            st.session_state["_enhanced_question"] = temp_state["enhanced_question"]

    # リクエスト名を復元
    if "_temp_request_name" in st.session_state:
        st.session_state["custom_request_name"] = st.session_state.pop("_temp_request_name")
        
        # 設定タブに切り替え
        st.session_state["active_settings_tab"] = 0
    
    # 質問を設定
    if next_question is not None:
        st.session_state["current_question"] = next_question
    elif "current_question" not in st.session_state:
        st.session_state["current_question"] = ""

def show():
    st.title("🤔 Simple Q&A")
    
    # セッション状態の初期化
    initialize_qa_state()

    # 質問フォームの表示
    st.markdown("### ❓ 質問を入力してください")
    
    # 質問の初期値を設定
    if "_enhanced_question" in st.session_state:
        # 改善された質問がある場合
        st.session_state["current_question"] = st.session_state.pop("_enhanced_question")
    elif "_next_question" in st.session_state:
        # 次のサイクルの質問がある場合
        st.session_state["current_question"] = st.session_state.pop("_next_question")
    elif "current_question" not in st.session_state:
        # 初期状態
        st.session_state["current_question"] = ""
    
    # 質問入力フォーム
    with st.form("qa_form", clear_on_submit=False):
        # 質問入力欄
        if "current_question" not in st.session_state:
            st.session_state["current_question"] = initial_question

        current_question = st.text_area(
            label="",
            key="current_question",
            height=100,
            help="AIに質問したい内容を入力してください",
            label_visibility="collapsed"
        )
        
        # オプション設定
        with st.expander("オプション設定", expanded=True):
            if "custom_request_name" not in st.session_state:
                st.session_state["custom_request_name"] = ""

            st.text_input(
                "リクエスト名（任意）",
                key="custom_request_name",
                help="保存時のリクエスト名を指定できます。空の場合は自動生成されます。",
                placeholder="例: 製品仕様の確認_20240305"
            )
        
        # 送信ボタン
        col1, col2 = st.columns(2)
        with col1:
            enhance_submitted = st.form_submit_button(
                "質問を改善",
                type="secondary",
                use_container_width=True
            )
        with col2:
            submitted = st.form_submit_button(
                "質問を送信",
                type="primary",
                use_container_width=True
            )

    # 質問改善の処理
    if enhance_submitted:
        if current_question and current_question.strip():
            try:
                # 現在の設定を保持
                current_settings = {
                    key: st.session_state.get(key) for key in [
                        "retrieval_mode", "top", "semantic_ranker",
                        "semantic_captions", "temperature",
                        "exclude_category", "prompt_template",
                        "custom_request_name"
                    ]
                }
                
                # 質問を改善
                enhanced_question = refine_query(current_question)
                
                # 一時的な状態を保存
                st.session_state["_temp_state"] = {
                    "settings": current_settings,
                    "enhanced_question": enhanced_question
                }

                # 現在のリクエスト名は保持
                if "custom_request_name" in st.session_state:
                    st.session_state["_temp_request_name"] = st.session_state["custom_request_name"]

                st.success("質問を改善しました")
                st.rerun()
            except Exception as e:
                st.error(f"質問の改善中にエラーが発生しました: {str(e)}")
        else:
            st.warning("質問を入力してから改善ボタンを押してください。")

    if enhance_submitted:
        question_text = st.session_state.get("current_question", "").strip()
        if question_text:
            try:
                # 質問を改善
                enhanced_question = refine_query(question_text)
                
                # 改善された質問を保存して再読み込み
                st.session_state["_enhanced_question"] = enhanced_question
                st.success("質問を改善しました")
                st.rerun()
            except Exception as e:
                st.error(f"質問の改善中にエラーが発生しました: {str(e)}")
        else:
            st.warning("質問を入力してから改善ボタンを押してください。")

    # 詳細設定の状態を管理
    detail_settings_key = "detail_settings_expanded"
    if detail_settings_key not in st.session_state:
        st.session_state[detail_settings_key] = False

    # 質問入力時のエンターキー対応
    st.markdown("""
        <script>
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey && document.activeElement.tagName === 'TEXTAREA') {
                e.preventDefault();
                document.querySelector('button[kind="primary"]').click();
            }
        });
        </script>
    """, unsafe_allow_html=True)

    def get_current_settings():
        """現在のウィジェットの値を取得"""
        settings = {}
        for key in ["retrieval_mode", "top", "semantic_ranker", "semantic_captions",
                   "temperature", "exclude_category", "prompt_template"]:
            temp_key = f"_{key}"
            if temp_key in st.session_state:
                settings[key] = st.session_state[temp_key]
        return settings
    
    def update_settings_and_state(settings):
        """設定と状態を更新（ウィジェットの値は変更しない）"""
        # UI状態を保存
        ui_state = {
            "detail_settings_expanded": st.session_state.get("detail_settings_expanded", False),
            "history_expanded": st.session_state.get("history_expanded", False)
        }
        
        # 永続的な設定値として保存
        for key, value in settings.items():
            st.session_state[key] = value
    
        # UI状態を復元
        for key, value in ui_state.items():
            st.session_state[key] = value

    # 設定タブの状態管理
    if "active_settings_tab" not in st.session_state:
        st.session_state["active_settings_tab"] = 0  # 0: 設定タブ, 1: 保存/読み込みタブ

    with st.expander("🛠️ リクエスト詳細設定", expanded=st.session_state[detail_settings_key]):
        settings_tab, io_tab = st.tabs(["設定", "設定の保存/読み込み"])
        
        # アクティブなタブを設定
        if st.session_state["active_settings_tab"] == 0:
            settings_tab.active = True
        else:
            io_tab.active = True
        
        # 設定タブ
        with settings_tab:
            placeholder = st.empty()
            with placeholder.container():
                # 設定ウィジェットを表示して現在の値を取得
                show_detail_settings()
                
                # 設定を同期するボタン
                if st.button("設定を適用", use_container_width=True):
                    settings = get_current_settings()
                    update_settings_and_state(settings)
                    st.success("設定を適用しました")
                    st.rerun()
        
        # 保存/読み込みタブ
        with io_tab:
            st.subheader("プリセット設定の管理")
            preset_col1, preset_col2 = st.columns(2)
            
            # 設定の保存
            with preset_col1:
                with st.form("save_settings_form", clear_on_submit=True):
                    preset_name = st.text_input("プリセット名", key="preset_name", placeholder="新しいプリセット")
                    if st.form_submit_button("設定を保存", use_container_width=True) and preset_name:
                        try:
                            # 現在のウィジェット値を取得
                            current_settings = get_current_settings()
                            
                            # 設定データを作成
                            settings = {
                                "approach": "rtr",
                                "overrides": current_settings
                            }
                            save_post_data(preset_name, settings)
                            st.success(f"設定 '{preset_name}' を保存しました")
                        except Exception as e:
                            st.error(f"設定の保存に失敗しました: {str(e)}")
            
            # 設定の読み込み
            with preset_col2:
                with st.form("load_settings_form", clear_on_submit=True):
                    presets = get_saved_post_data_names()
                    if presets:
                        preset = st.selectbox(
                            "保存済み設定",
                            options=[""] + presets,
                            key="load_preset",
                            format_func=lambda x: "設定を選択" if x == "" else x
                        )
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            load_submitted = st.form_submit_button("読み込む", use_container_width=True)
                        with col2:
                            delete_submitted = st.form_submit_button("削除", type="secondary", use_container_width=True)
                        
                        if load_submitted and preset:
                            try:
                                # 設定を読み込む
                                settings = load_post_data(preset)
                                if settings and "overrides" in settings:
                                    # 永続的な設定値を更新
                                    for key, value in settings["overrides"].items():
                                        st.session_state[key] = value
                                    
                                    # 次のレンダリングサイクルで使用する値を保存
                                    st.session_state["_temp_settings"] = settings["overrides"]
                                    
                                    # 設定タブに切り替え
                                    st.session_state["active_settings_tab"] = 0
                                    
                                    st.success(f"設定 '{preset}' を読み込みました")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"設定の読み込みに失敗しました: {str(e)}")
                        
                        if delete_submitted and preset:
                            try:
                                delete_post_data(preset)
                                st.success(f"設定 '{preset}' を削除しました")
                                st.rerun()
                            except Exception as e:
                                st.error(f"設定の削除に失敗しました: {str(e)}")
            
            # インポート/エクスポート
            st.divider()
            st.subheader("インポート/エクスポート")
            imp_exp_col1, imp_exp_col2 = st.columns(2)
            
            # エクスポート
            with imp_exp_col1:
                if st.button("すべての設定をエクスポート", use_container_width=True):
                    settings = get_all_post_data()
                    settings_json = json.dumps(settings, ensure_ascii=False, indent=2)
                    st.download_button(
                        "JSONとしてダウンロード",
                        settings_json,
                        file_name="qa_settings.json",
                        mime="application/json",
                        use_container_width=True
                    )
            
            # インポート
            with imp_exp_col2:
                uploaded_file = st.file_uploader(
                    "設定をインポート",
                    type=["json"],
                    label_visibility="collapsed",
                    key="settings_import"
                )
                if uploaded_file is not None:
                    try:
                        imported_settings = json.load(uploaded_file)
                        # データ構造を修正してインポート
                        modified_settings = {}
                        for name, data in imported_settings.items():
                            if isinstance(data, dict):
                                if "overrides" not in data:
                                    overrides = {k: v for k, v in data.items() if k not in ["question", "approach"]}
                                    data = {"overrides": overrides, "approach": "rtr"}
                                modified_settings[name] = data
                        success, errors = import_post_data(modified_settings)
                        if success > 0:
                            st.success(f"設定をインポートしました（成功: {success}, エラー: {errors}）")
                            # 設定タブに切り替え
                            st.session_state["active_settings_tab"] = 0
                            initialize_qa_state()
                            st.rerun()
                        else:
                            st.warning("インポートできる設定がありませんでした")
                    except Exception as e:
                        st.error(f"設定のインポートに失敗しました: {str(e)}")

            st.divider()

    # Handle form submission
    if submitted:
        with st.spinner("AIが回答を生成中..."):
            try:
                # 質問を取得
                current_question = st.session_state.get("current_question", "")

                # 現在の設定値を取得
                current_settings = {}
                for key in ["retrieval_mode", "top", "semantic_ranker", "semantic_captions",
                           "temperature", "exclude_category", "prompt_template"]:
                    current_settings[key] = st.session_state.get(key)

                # JSONデータを作成（現在の設定値を使用）
                data = {
                    "question": current_question,
                    "approach": "rtr",
                    "overrides": {
                        "retrieval_mode": str(current_settings["retrieval_mode"]),
                        "semantic_ranker": bool(current_settings["semantic_ranker"]),
                        "semantic_captions": bool(current_settings["semantic_captions"]),
                        "top": int(current_settings["top"]),
                        "temperature": float(current_settings["temperature"]),
                        "prompt_template": str(current_settings["prompt_template"]),
                        "exclude_category": str(current_settings["exclude_category"])
                    }
                }

                # 一時的な値として次のサイクル用の質問を保存
                st.session_state["_next_question"] = current_question
                
                # リクエストの送信と応答の処理
                response = make_request(
                    "POST",
                    "/ask",
                    json.dumps(data)
                )

                # リクエスト名を生成
                request_name = (
                    st.session_state.get("custom_request_name", "").strip() or
                    f"Simple Q&A_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )

                # リクエスト履歴を保存
                from utils.db_utils import save_request
                save_request(
                    target_url=st.session_state.get("target_url", ""),
                    post_data=json.dumps(data),
                    response=response,
                    proxy_url=st.session_state.get("proxy_url", ""),
                    request_name=request_name
                )

                # リクエスト名をクリア
                if "custom_request_name" in st.session_state:
                    del st.session_state["custom_request_name"]

                # エラーチェック
                if "error" in response and response["error"]:
                    st.error(f"エラーが発生しました: {response['error']}")
                    return

                # 回答の表示
                if "answer" in response:
                    st.markdown("### 💡 回答")
                    with st.container():
                        # 回答本文
                        with st.expander("回答内容", expanded=True):
                            st.write(response["answer"])
                        
                        # 参照情報
                        if "data_points" in response:
                            with st.expander("🔍 参照情報", expanded=False):
                                for i, point in enumerate(response["data_points"], 1):
                                    st.markdown(f"**{i}.** {point}")
                                    if i < len(response["data_points"]):
                                        st.divider()
                        
                        # 思考プロセス
                        if "thoughts" in response:
                            with st.expander("💭 思考プロセス", expanded=False):
                                st.write(response["thoughts"])

            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
    # 履歴表示の状態を管理
    history_key = "history_expanded"
    if history_key not in st.session_state:
        st.session_state[history_key] = False

    st.markdown("### 📜 履歴")
    with st.container():
        history_expander = st.expander(
            "履歴一覧",
            expanded=st.session_state[history_key]
        )
    
    with history_expander:
        # フィルター
        filter_name = st.text_input("履歴を検索", key="filter_name")
        
        # データ読み込み
        requests = load_requests_summary()
        if requests is not None and not requests.empty:
            # フィルター適用
            if filter_name:
                requests = requests[requests['request_name'].str.contains(filter_name, case=False, na=False)]

            # カラム選択
            st.subheader("表示カラムの選択")
            columns = {
                "request_time": "日時",
                "request_name": "リクエスト名",
                "url": "URL",
                "status_code": "ステータスコード",
                "question": "質問",
                "error": "エラー",
                "answer": "回答",
                "thoughts": "思考プロセス",
                "data_points": "参照情報",
                "prompt_template": "プロンプトテンプレート",
                "memo": "メモ"
            }

            selected_columns = st.multiselect(
                "表示するカラムを選択",
                list(columns.keys()),
                default=["request_time", "request_name", "question", "prompt_template", "answer", "data_points", "memo"],
                format_func=lambda x: columns[x]
            )

            # メモ編集用のフォーム
            with st.form("memo_edit_form"):
                edited_df = st.data_editor(
                    requests[selected_columns],
                    column_config={
                        "memo": st.column_config.TextColumn(
                            "メモ",
                            help="クリックして編集",
                            width="medium"
                        ),
                        "request_time": st.column_config.DatetimeColumn(
                            "日時",
                            width="small",
                            format="YYYY-MM-DD HH:mm:ss"
                        ),
                        "question": st.column_config.TextColumn(
                            "質問",
                            width="medium"
                        ),
                        "answer": st.column_config.TextColumn(
                            "回答",
                            width="large"
                        ),
                        "data_points": st.column_config.TextColumn(
                            "参照情報",
                            width="large"
                        )
                    },
                    hide_index=True,
                    key="requests_table"
                )

                if st.form_submit_button("メモを保存"):
                    try:
                        # 変更されたメモを保存
                        for idx, row in edited_df.iterrows():
                            original_memo = requests.iloc[idx]["memo"]
                            if pd.isna(original_memo):
                                original_memo = ""
                            new_memo = row["memo"] if not pd.isna(row["memo"]) else ""

                            if original_memo != new_memo:
                                update_request_memo(requests.iloc[idx]["request_name"], new_memo)

                        # メモの変更を反映するためにデータを再読み込み
                        requests = load_requests_summary()
                        if filter_name:
                            requests = requests[requests['request_name'].str.contains(filter_name, case=False, na=False)]
                        st.success("メモを保存しました")
                    except Exception as e:
                        st.error(f"メモの保存中にエラーが発生しました: {str(e)}")

            # CSVエクスポート
            if st.button("履歴をCSVでエクスポート"):
                try:
                    # エクスポート用のデータフレームを準備
                    export_df = requests[selected_columns].copy()
                    
                    # 日本語文字列を適切にエンコード
                    for col in export_df.columns:
                        if export_df[col].dtype == 'object':
                            export_df[col] = export_df[col].fillna('').astype(str)
                    
                    # CSVデータを生成（BOMありUTF-8）
                    csv_data = export_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                    
                    now = datetime.now().strftime('%Y%m%d_%H%M%S')
                    st.download_button(
                        label="CSVをダウンロード",
                        data=csv_data,
                        file_name=f"qa_history_{now}.csv",
                        mime="text/csv;charset=utf-8-sig"
                    )
                except Exception as e:
                    st.error(f"CSVエクスポート中にエラーが発生しました: {str(e)}")

            # 履歴の削除
            st.divider()
            st.caption("⚠️ 履歴の削除")
            col1, col2 = st.columns([3, 1])
            with col1:
                request_to_delete = st.selectbox(
                    "削除する履歴を選択",
                    requests['request_name'].tolist(),
                    key="request_to_delete"
                )
            with col2:
                if st.button("選択した履歴を削除", use_container_width=True):
                    try:
                        # 現在のexpander状態を保持
                        history_expanded = st.session_state.get("history_expanded", False)
                        detail_expanded = st.session_state.get("detail_settings_expanded", False)

                        # 削除を実行
                        delete_request(request_to_delete)
                        st.success("履歴を削除しました")

                        # expander状態を維持して画面を更新
                        st.session_state["history_expanded"] = history_expanded
                        st.session_state["detail_settings_expanded"] = detail_expanded
                        st.rerun()
                    except Exception as e:
                        st.error(f"履歴の削除中にエラーが発生しました: {str(e)}")
        else:
            st.info("履歴がありません")