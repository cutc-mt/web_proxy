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
def initialize_qa_state():
    """Simple Q&Aのセッション状態を初期化"""
    if "load_count" not in st.session_state:
        st.session_state.load_count = 0
        
    current_count = st.session_state.load_count
    
    # 保存された設定があればそれを読み込む
    if "temp_settings" in st.session_state and st.session_state.temp_settings is not None:
        try:
            settings = st.session_state.temp_settings
            if isinstance(settings, dict) and "overrides" in settings:
                overrides = settings["overrides"]
                # 設定を適用
                st.session_state[f"question_{current_count}"] = settings.get("question", "")
                st.session_state[f"retrieval_mode_{current_count}"] = str(overrides.get("retrieval_mode", "hybrid"))
                st.session_state[f"top_{current_count}"] = int(overrides.get("top", 3))
                st.session_state[f"semantic_ranker_{current_count}"] = bool(overrides.get("semantic_ranker", True))
                st.session_state[f"semantic_captions_{current_count}"] = bool(overrides.get("semantic_captions", False))
                st.session_state[f"temperature_{current_count}"] = float(overrides.get("temperature", 0.3))
                st.session_state[f"exclude_category_{current_count}"] = str(overrides.get("exclude_category", ""))
                st.session_state[f"prompt_template_{current_count}"] = str(overrides.get("prompt_template", ""))
                
                # 一時保存データをクリア
                st.session_state.temp_settings = None
                st.session_state.temp_preset_name = None
                return
        except Exception as e:
            st.error(f"設定の読み込みに失敗しました: {str(e)}")
    
    # 保存された設定がない場合はデフォルト値で初期化
    if f"question_{current_count}" not in st.session_state:
        st.session_state[f"question_{current_count}"] = ""
    if f"retrieval_mode_{current_count}" not in st.session_state:
        st.session_state[f"retrieval_mode_{current_count}"] = "hybrid"
    if f"top_{current_count}" not in st.session_state:
        st.session_state[f"top_{current_count}"] = 3
    if f"semantic_ranker_{current_count}" not in st.session_state:
        st.session_state[f"semantic_ranker_{current_count}"] = True
    if f"semantic_captions_{current_count}" not in st.session_state:
        st.session_state[f"semantic_captions_{current_count}"] = False
    if f"temperature_{current_count}" not in st.session_state:
        st.session_state[f"temperature_{current_count}"] = 0.3
    if f"exclude_category_{current_count}" not in st.session_state:
        st.session_state[f"exclude_category_{current_count}"] = ""
    if f"prompt_template_{current_count}" not in st.session_state:
        st.session_state[f"prompt_template_{current_count}"] = ""
        
    # UI状態の初期化
    if "detail_settings_expanded" not in st.session_state:
        st.session_state.detail_settings_expanded = False
    if "history_expanded" not in st.session_state:
        st.session_state.history_expanded = False
    

def show():
    st.title("🤔 Simple Q&A")
    
    # セッション状態の初期化
    initialize_qa_state()

    current_count = st.session_state.get('load_count', 0)

    # 質問フィールドの初期化
    question_key = f"question_{current_count}"
    if question_key not in st.session_state:
        st.session_state[question_key] = ""

    # 質問入力フォーム
    st.markdown("### ❓ 質問を入力してください")
    
    with st.form("qa_form", clear_on_submit=False):
        current_question = st.text_area(
            label="",
            key=question_key,
            height=100,
            help="AIに質問したい内容を入力してください",
            label_visibility="collapsed"
        )
        
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
    if enhance_submitted and current_question.strip():
        # 質問を改善
        enhanced_question = refine_query(current_question)
        # 新しい状態を作成
        st.session_state.load_count += 1
        new_count = st.session_state.load_count
        # 改善された質問を新しい状態に設定
        st.session_state[f"question_{new_count}"] = enhanced_question
        # 画面を更新
        st.rerun()
    elif enhance_submitted:
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

    detail_expander = st.expander(
        "🛠️ リクエスト詳細設定",
        expanded=st.session_state[detail_settings_key]
    )

    with detail_expander:
        # 検索設定
        st.subheader("検索設定")
        col1, col2 = st.columns(2)
        with col1:
            # 現在の値またはデフォルト値のインデックスを取得
            modes = ["hybrid", "vectors", "text"]
            current_mode = st.session_state.get(f"retrieval_mode_{current_count}", "hybrid")
            mode_index = modes.index(current_mode) if current_mode in modes else 0
            
            st.selectbox(
                "検索モード",
                modes,
                index=mode_index,
                key=f"retrieval_mode_{current_count}",
                help="ドキュメントの検索方法を選択"
            )
            
            # セッション状態に値がある場合はそれを使用し、なければデフォルト値を使用
            top_key = f"top_{current_count}"
            if top_key not in st.session_state:
                st.session_state[top_key] = 3
            
            st.number_input(
                "参照件数",
                min_value=1,
                max_value=50,
                key=top_key,
                help="AIが参照するドキュメントの数"
            )

        with col2:
            # セッション状態に値がある場合はそれを使用し、なければデフォルト値を使用
            semantic_ranker_key = f"semantic_ranker_{current_count}"
            if semantic_ranker_key not in st.session_state:
                st.session_state[semantic_ranker_key] = True
            
            st.checkbox(
                "セマンティック検索",
                key=semantic_ranker_key,
                help="意味を考慮した検索を使用"
            )
            
            # セッション状態に値がある場合はそれを使用し、なければデフォルト値を使用
            semantic_captions_key = f"semantic_captions_{current_count}"
            if semantic_captions_key not in st.session_state:
                st.session_state[semantic_captions_key] = False
            
            st.checkbox(
                "セマンティックキャプション",
                key=semantic_captions_key,
                help="ドキュメントの要約を生成"
            )

        # 生成設定
        st.subheader("生成設定")
        # セッション状態に値がある場合はそれを使用し、なければデフォルト値を使用
        temperature_key = f"temperature_{current_count}"
        if temperature_key not in st.session_state:
            st.session_state[temperature_key] = 0.3
        
        st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            step=0.1,
            key=temperature_key,
            help="値が大きいほど創造的な回答になります"
        )

        # 除外カテゴリの初期化
        exclude_category_key = f"exclude_category_{current_count}"
        if exclude_category_key not in st.session_state:
            st.session_state[exclude_category_key] = ""
        
        st.text_area(
            "除外カテゴリ（カンマ区切り）",
            key=exclude_category_key,
            help="特定のカテゴリを検索から除外"
        )

        # プロンプトテンプレートの初期化
        prompt_template_key = f"prompt_template_{current_count}"
        if prompt_template_key not in st.session_state:
            st.session_state[prompt_template_key] = ""
        
        st.text_area(
            "プロンプトテンプレート",
            key=prompt_template_key,
            help="AIへの指示テンプレート"
        )

        st.divider()

        # エクスポート/インポート
        st.subheader("設定のエクスポート/インポート")
        col1, col2 = st.columns(2)
        with col1:
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
        with col2:
            uploaded_file = st.file_uploader("設定をインポート", type=["json"], label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    imported_settings = json.load(uploaded_file)
                    # データ構造を修正してインポート
                    modified_settings = {}
                    for name, data in imported_settings.items():
                        if isinstance(data, dict):
                            if "overrides" not in data:
                                overrides = {k: v for k, v in data.items() if k not in ["question", "approach"]}
                                data = {"overrides": overrides, "question": "", "approach": "rtr"}
                            modified_settings[name] = data
                    success, errors = import_post_data(modified_settings)
                    st.success(f"設定をインポートしました（成功: {success}, エラー: {errors}）")
                    # 設定を再読み込み
                    st.session_state.load_count += 1
                    initialize_qa_state()
                except Exception as e:
                    st.error(f"設定のインポートに失敗しました: {str(e)}")

        st.divider()

        # 設定の保存・読み込み
        col1, col2 = st.columns(2)
        with col1:
            with st.form("save_settings_form_detail"):
                preset_name = st.text_input("プリセット名", key="qa_preset_name_detail", placeholder="新しいプリセット")
                save_submitted = st.form_submit_button("設定を保存", use_container_width=True)
                if save_submitted and preset_name:
                    try:
                        settings = {
                            "question": "",
                            "approach": "rtr",
                            "overrides": {
                                "retrieval_mode": str(st.session_state[f"retrieval_mode_{current_count}"]),
                                "top": int(st.session_state[f"top_{current_count}"]),
                                "semantic_ranker": bool(st.session_state[f"semantic_ranker_{current_count}"]),
                                "semantic_captions": bool(st.session_state[f"semantic_captions_{current_count}"]),
                                "temperature": float(st.session_state[f"temperature_{current_count}"]),
                                "exclude_category": str(st.session_state[f"exclude_category_{current_count}"]),
                                "prompt_template": str(st.session_state[f"prompt_template_{current_count}"])
                            }
                        }
                        save_post_data(preset_name, settings)
                        st.success(f"設定 '{preset_name}' を保存しました")
                        
                        # 設定を一時保存
                        st.session_state["temp_settings"] = settings
                        st.session_state["temp_preset_name"] = preset_name
                        
                        # 次の状態を初期化
                        st.session_state.load_count += 1
                        
                        # 画面を更新
                        st.rerun()
                    except Exception as e:
                        st.error(f"設定の保存に失敗しました: {str(e)}")

        with col2:
            with st.form("load_settings_form_detail"):
                presets = get_saved_post_data_names()
                if presets:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        preset = st.selectbox(
                            "保存済み設定",
                            options=[""] + presets,
                            format_func=lambda x: "設定を選択" if x == "" else x
                        )
                    with col2:
                        load_submitted = st.form_submit_button("読み込む", use_container_width=True)
                        if load_submitted and preset:
                            try:
                                settings = load_post_data(preset)
                                if not settings:
                                    st.error(f"設定 '{preset}' が見つかりません")
                                    return

                                if not isinstance(settings, dict) or "overrides" not in settings:
                                    st.error(f"設定 '{preset}' の形式が無効です")
                                    return

                                # expanderの状態を保存
                                detail_expanded = st.session_state.get("detail_settings_expanded", False)
                                history_expanded = st.session_state.get("history_expanded", False)
                                
                                try:
                                    # 設定を一時保存
                                    st.session_state["temp_settings"] = settings
                                    st.session_state["temp_preset_name"] = preset
                                    
                                    # expanderの状態を保持
                                    detail_expanded = st.session_state.get("detail_settings_expanded", False)
                                    history_expanded = st.session_state.get("history_expanded", False)
                                    
                                    # 次の状態のために更新
                                    st.session_state.load_count += 1
                                    
                                    # expander状態を維持
                                    st.session_state["detail_settings_expanded"] = detail_expanded
                                    st.session_state["history_expanded"] = history_expanded
                                    
                                    st.success(f"設定 '{preset}' を読み込みました")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"設定の一時保存でエラー: {str(e)}")
                                    raise
                            except Exception as e:
                                st.error(f"設定の読み込みに失敗しました: {str(e)}")
                    with col3:
                        delete_submitted = st.form_submit_button("削除", type="secondary", use_container_width=True)
                        if delete_submitted and preset:
                            if preset:
                                try:
                                    delete_post_data(preset)
                                    st.success(f"設定 '{preset}' を削除しました")
                                    # セッション状態をクリア
                                    st.session_state["temp_settings"] = None
                                    st.session_state["temp_preset_name"] = None
                                    # 次の状態に進む
                                    st.session_state.load_count += 1
                                    # 画面を強制的に更新
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"設定の削除中にエラーが発生しました: {str(e)}")

    # Handle form submission
    if submitted:
        with st.spinner("AIが回答を生成中..."):
            try:
                # 現在の質問を保存
                current_question = st.session_state[f"question_{current_count}"]
                st.session_state["last_question"] = current_question
                
                # 現在のカウントの値を使用してJSONデータを作成
                current_count = st.session_state.load_count
                data = {
                    "question": current_question,
                    "approach": "rtr",
                    "overrides": {
                        "retrieval_mode": st.session_state[f"retrieval_mode_{current_count}"],
                        "semantic_ranker": st.session_state[f"semantic_ranker_{current_count}"],
                        "semantic_captions": st.session_state[f"semantic_captions_{current_count}"],
                        "top": st.session_state[f"top_{current_count}"],
                        "temperature": st.session_state[f"temperature_{current_count}"],
                        "prompt_template": st.session_state[f"prompt_template_{current_count}"],
                        "exclude_category": st.session_state[f"exclude_category_{current_count}"]
                    }
                }

                # 現在のexpander状態を保持
                detail_expanded = st.session_state.get("detail_settings_expanded", False)
                history_expanded = st.session_state.get("history_expanded", False)
                
                # カウントを進める
                st.session_state.load_count += 1
                current_count = st.session_state.load_count
                
                # フォームの状態をリセット
                st.session_state[f"question_{current_count}"] = ""
                st.session_state[f"retrieval_mode_{current_count}"] = "hybrid"
                st.session_state[f"top_{current_count}"] = 3
                st.session_state[f"semantic_ranker_{current_count}"] = True
                st.session_state[f"semantic_captions_{current_count}"] = False
                st.session_state[f"temperature_{current_count}"] = 0.3
                st.session_state[f"exclude_category_{current_count}"] = ""
                st.session_state[f"prompt_template_{current_count}"] = ""
                
                # expander状態を維持
                st.session_state["detail_settings_expanded"] = detail_expanded
                st.session_state["history_expanded"] = history_expanded
                
                # リクエストの送信（/askパスを指定）
                response = make_request(
                    "POST",
                    "/ask",
                    json.dumps(data)
                )

                # リクエスト履歴を保存
                from utils.db_utils import save_request
                save_request(
                    target_url=st.session_state.get("target_url", ""),
                    post_data=json.dumps(data),
                    response=response,
                    proxy_url=st.session_state.get("proxy_url", ""),
                    request_name=f"Simple Q&A_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )

                if "error" in response and response["error"]:
                    st.error(f"エラーが発生しました: {response['error']}")
                    return

                # 回答セクション
                st.markdown("### 💡 回答")
                with st.container():
                    if "answer" in response:
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