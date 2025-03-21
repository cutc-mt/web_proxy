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

def show_detail_settings():
    """詳細設定のウィジェットを表示"""
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

    current_settings = {
        "retrieval_mode": st.session_state.get("_retrieval_mode"),
        "top": st.session_state.get("_top"),
        "semantic_ranker": st.session_state.get("_semantic_ranker"),
        "semantic_captions": st.session_state.get("_semantic_captions"),
        "temperature": st.session_state.get("_temperature"),
        "exclude_category": st.session_state.get("_exclude_category"),
        "prompt_template": st.session_state.get("_prompt_template")
    }

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

def get_default_settings():
    """デフォルトの設定値を返す"""
    return {
        "retrieval_mode": "hybrid",
        "top": 3,
        "semantic_ranker": True,
        "semantic_captions": False,
        "temperature": 0.3,
        "exclude_category": "",
        "prompt_template": "",
        "detail_settings_expanded": False,
        "history_expanded": False
    }

def get_current_settings():
    """現在の設定値を取得"""
    settings = {}
    keys = [
        "retrieval_mode", "top", "semantic_ranker", "semantic_captions",
        "temperature", "exclude_category", "prompt_template"
    ]
    
    for key in keys:
        temp_key = f"_{key}"
        if temp_key in st.session_state:
            settings[key] = st.session_state[temp_key]
        else:
            settings[key] = st.session_state.get(key, get_default_settings()[key])
    return settings

def update_settings(settings):
    """設定を更新"""
    ui_state = {
        "detail_settings_expanded": st.session_state.get("detail_settings_expanded", False),
        "history_expanded": st.session_state.get("history_expanded", False),
        "active_settings_tab": st.session_state.get("active_settings_tab", 0)
    }
    
    for key, value in settings.items():
        st.session_state[key] = value
    
    for key, value in ui_state.items():
        st.session_state[key] = value

def initialize_qa_state():
    """Simple Q&Aのセッション状態を初期化"""
    next_question = st.session_state.pop("_next_question", None)
    
    for key, value in get_default_settings().items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    if "_temp_state" in st.session_state:
        temp_state = st.session_state.pop("_temp_state")
        if "settings" in temp_state:
            update_settings(temp_state["settings"])
        if "enhanced_question" in temp_state:
            st.session_state["_enhanced_question"] = temp_state["enhanced_question"]

    if "_temp_request_name" in st.session_state:
        st.session_state["custom_request_name"] = st.session_state.pop("_temp_request_name")
        st.session_state["active_settings_tab"] = 0
    
    st.session_state["current_question"] = next_question if next_question is not None else st.session_state.get("current_question", "")

def render_settings_panel():
    """設定パネルのレンダリング"""
    with st.sidebar.expander("⚙️ 詳細設定", expanded=False):
        # タブの表示と内容の切り替え
        tabs = ["設定", "設定の保存/読み込み"]
        
        current_tab = st.radio(
            "タブ選択",
            tabs,
            label_visibility="collapsed",
            index=st.session_state.get("active_settings_tab", 0)
        )
        
        new_tab_index = tabs.index(current_tab)
        if new_tab_index != st.session_state.get("active_settings_tab", 0):
            st.session_state["active_settings_tab"] = new_tab_index
            st.rerun()
        
        if current_tab == "設定":
            show_detail_settings()
            if st.button("設定を適用", use_container_width=True):
                current_settings = {
                    "retrieval_mode": st.session_state.get("_retrieval_mode"),
                    "top": st.session_state.get("_top"),
                    "semantic_ranker": st.session_state.get("_semantic_ranker"),
                    "semantic_captions": st.session_state.get("_semantic_captions"),
                    "temperature": st.session_state.get("_temperature"),
                    "exclude_category": st.session_state.get("_exclude_category"),
                    "prompt_template": st.session_state.get("_prompt_template")
                }
                for key, value in current_settings.items():
                    if value is not None:
                        st.session_state[key] = value
                st.success("設定を適用しました")
                st.rerun()
        
        else:
            st.subheader("プリセット設定の管理")
            
            # 設定の保存
            preset_name = st.text_input("プリセット名", key="preset_name", placeholder="新しいプリセット")
            if st.button("設定を保存", use_container_width=True) and preset_name:
                try:
                    current_settings = get_current_settings()
                    settings = {
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
                    save_post_data(preset_name, settings)
                    st.success(f"設定 '{preset_name}' を保存しました")
                except Exception as e:
                    st.error(f"設定の保存に失敗しました: {str(e)}")
            
            # 設定の読み込み
            presets = get_saved_post_data_names()
            if presets:
                st.subheader("保存済み設定の管理")
                preset = st.selectbox(
                    "保存済み設定",
                    options=[""] + presets,
                    key="load_preset",
                    format_func=lambda x: "設定を選択" if x == "" else x
                )
                
                if preset:
                    if st.button("読み込む", use_container_width=True):
                        try:
                            settings = load_post_data(preset)
                            if settings and "overrides" in settings:
                                for key, value in settings["overrides"].items():
                                    st.session_state[key] = value
                                st.session_state["_temp_settings"] = settings["overrides"]
                                st.session_state["active_settings_tab"] = 0
                                st.success(f"設定 '{preset}' を読み込みました")
                                st.rerun()
                        except Exception as e:
                            st.error(f"設定の読み込みに失敗しました: {str(e)}")

                    if st.button("削除", use_container_width=True):
                        try:
                            delete_post_data(preset)
                            st.success(f"設定 '{preset}' を削除しました")
                            st.rerun()
                        except Exception as e:
                            st.error(f"設定の削除に失敗しました: {str(e)}")

            st.divider()
            st.subheader("インポート/エクスポート")
            
            # エクスポート
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
            uploaded_file = st.file_uploader(
                "設定をインポート",
                type=["json"],
                label_visibility="collapsed"
            )
            if uploaded_file is not None:
                try:
                    imported_settings = json.load(uploaded_file)
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
                        st.session_state["active_settings_tab"] = 0
                        initialize_qa_state()
                        st.rerun()
                    else:
                        st.warning("インポートできる設定がありませんでした")
                except Exception as e:
                    st.error(f"設定のインポートに失敗しました: {str(e)}")

def show():
    """Simple Q&A ページの表示"""
    st.title("🤔 Simple Q&A")
    
    # セッション状態の初期化
    initialize_qa_state()

    # サイドバーに設定パネルを表示
    render_settings_panel()

    # 質問入力フォーム
    st.markdown("### ❓ 質問を入力してください")
    
    # 過去の質問サジェスト
    with st.expander("💭 過去の質問から選択", expanded=False):
        requests = load_requests_summary()
        if requests is not None and not requests.empty:
            unique_questions = requests['question'].dropna().unique()
            
            if 'unique_questions_list' not in st.session_state:
                st.session_state['unique_questions_list'] = list(unique_questions)
            
            for i, question in enumerate(st.session_state['unique_questions_list']):
                display_text = (question[:100] + "...") if len(question) > 100 else question
                tooltip = question if len(question) > 100 else None
                
                if st.button(
                    display_text,
                    key=f"q_{i}",
                    use_container_width=True,
                    help=tooltip
                ):
                    st.session_state["current_question"] = question
                    st.rerun()

    # 質問入力フォーム
    with st.form("qa_form", clear_on_submit=False):
        current_question = st.text_area(
            label="",
            key="current_question",
            height=200,
            help="AIに質問したい内容を入力してください。💭 過去の質問から選択することもできます。",
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
        question_text = current_question.strip() if current_question else ""
        if not question_text:
            st.warning("質問を入力してから改善ボタンを押してください。")
            return

        try:
            current_settings = get_current_settings()
            enhanced_question = refine_query(question_text)
            
            st.session_state["_temp_state"] = {
                "settings": current_settings,
                "enhanced_question": enhanced_question
            }

            if "custom_request_name" in st.session_state:
                st.session_state["_temp_request_name"] = st.session_state["custom_request_name"]

            st.success("質問を改善しました")
            st.rerun()
        except Exception as e:
            st.error(f"質問の改善中にエラーが発生しました: {str(e)}")

    # 質問送信の処理
    if submitted:
        with st.spinner("AIが回答を生成中..."):
            try:
                question_text = st.session_state.get("current_question", "").strip()
                if not question_text:
                    st.warning("質問を入力してください。")
                    return

                current_settings = get_current_settings()
                data = {
                    "question": question_text,
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

                st.session_state["_next_question"] = current_question
                
                response = make_request(
                    "POST",
                    "/ask",
                    json.dumps(data)
                )

                request_name = (
                    st.session_state.get("custom_request_name", "").strip() or
                    f"Simple Q&A_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )

                save_request(
                    target_url=st.session_state.get("target_url", ""),
                    post_data=json.dumps(data),
                    response=response,
                    proxy_url=st.session_state.get("proxy_url", ""),
                    request_name=request_name
                )

                if "custom_request_name" in st.session_state:
                    del st.session_state["custom_request_name"]

                if "error" in response and response["error"]:
                    st.error(f"エラーが発生しました: {response['error']}")
                    return

                if "answer" in response:
                    st.markdown("### 💡 回答")
                    with st.container():
                        with st.expander("回答内容", expanded=True):
                            st.write(response["answer"])
                        
                        if "data_points" in response:
                            with st.expander("🔍 参照情報", expanded=False):
                                for i, point in enumerate(response["data_points"], 1):
                                    st.markdown(f"**{i}.** {point}")
                                    if i < len(response["data_points"]):
                                        st.divider()
                        
                        if "thoughts" in response:
                            with st.expander("💭 思考プロセス", expanded=False):
                                st.write(response["thoughts"])

            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")

    # 履歴の表示
    st.markdown("### 📜 履歴")
    with st.expander("履歴一覧", expanded=st.session_state.get("history_expanded", False)):
        filter_name = st.text_input("履歴を検索", key="filter_name")
        
        requests = load_requests_summary()
        if requests is not None and not requests.empty:
            if filter_name:
                requests = requests[requests['request_name'].str.contains(filter_name, case=False, na=False)]

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
                        for idx, row in edited_df.iterrows():
                            original_memo = requests.iloc[idx]["memo"]
                            if pd.isna(original_memo):
                                original_memo = ""
                            new_memo = row["memo"] if not pd.isna(row["memo"]) else ""

                            if original_memo != new_memo:
                                update_request_memo(requests.iloc[idx]["request_name"], new_memo)

                        requests = load_requests_summary()
                        if filter_name:
                            requests = requests[requests['request_name'].str.contains(filter_name, case=False, na=False)]
                        st.success("メモを保存しました")
                    except Exception as e:
                        st.error(f"メモの保存中にエラーが発生しました: {str(e)}")

            if st.button("履歴をCSVでエクスポート"):
                try:
                    export_df = requests[selected_columns].copy()
                    
                    for col in export_df.columns:
                        if export_df[col].dtype == 'object':
                            export_df[col] = export_df[col].fillna('').astype(str)
                    
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
                        history_expanded = st.session_state.get("history_expanded", False)
                        detail_expanded = st.session_state.get("detail_settings_expanded", False)

                        delete_request(request_to_delete)
                        st.success("履歴を削除しました")

                        st.session_state["history_expanded"] = history_expanded
                        st.session_state["detail_settings_expanded"] = detail_expanded
                        st.rerun()
                    except Exception as e:
                        st.error(f"履歴の削除中にエラーが発生しました: {str(e)}")
        else:
            st.info("履歴がありません")