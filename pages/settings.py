import streamlit as st
from utils.db_utils import save_urls, load_urls, get_saved_url_names
from utils.api_utils import is_valid_proxy_url
from utils.chat_backends.manager import ChatBackendManager

def show():
    """設定ページの表示"""
    st.title("⚙️ 設定")
    
    # バックエンド毎のURL設定
    st.header("バックエンド別のURL設定")
    
    # 利用可能なバックエンドを取得
    backend_manager = ChatBackendManager()
    backends = backend_manager.get_available_backends()
    backend_names = list(backends.keys())

    # バックエンドの選択
    selected_backend = st.selectbox(
        "バックエンド",
        backend_names,
        index=backend_names.index("azure_openai_legacy") if "azure_openai_legacy" in backend_names else 0
    )
    
    # 選択されたバックエンドの設定を読み込む
    try:
        saved_urls = load_urls(selected_backend)
        initial_target_url = saved_urls.get("target_url", "") if saved_urls else ""
        initial_proxy_url = saved_urls.get("proxy_url", "") if saved_urls else ""
    except Exception as e:
        st.error(f"URL設定の読み込みに失敗しました: {str(e)}")
        initial_target_url = ""
        initial_proxy_url = ""
    
    with st.form(f"url_settings_form_{selected_backend}", clear_on_submit=False):
        st.markdown("""
        ℹ️ ターゲットURLはベースURLのみを入力してください。
        例: `https://api.example.com`
        """)
        
        # Target URLの入力フィールド
        target_url = st.text_input(
            f"{selected_backend} のターゲットURL",
            value=initial_target_url,
            help="APIのベースURLを入力してください（/chatや/askは不要）",
            placeholder="https://api.example.com"
        )

        # Proxy URLの入力フィールド
        proxy_url = st.text_input(
            f"{selected_backend} のプロキシURL（オプション）",
            value=initial_proxy_url,
            help="プロキシが必要な場合はURLを入力してください",
            placeholder="http://proxy.example.com"
        )

        # プロキシURLの形式チェック
        if proxy_url and not is_valid_proxy_url(proxy_url):
            st.error("プロキシURLの形式が正しくありません")
            valid_proxy = False
        else:
            valid_proxy = True

        # 中央寄せのサブミットボタン
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                f"{selected_backend} の設定を保存",
                type="primary",
                use_container_width=True
            )

        # フォーム送信時の処理
        if submitted:
            # バリデーションチェック
            if not target_url:
                st.error("ターゲットURLを入力してください")
                return
            
            if proxy_url and not valid_proxy:
                st.error("プロキシURLの形式が正しくないため、保存できません")
                return

            # 末尾のスラッシュを削除
            target_url = target_url.rstrip('/')
            if proxy_url:
                proxy_url = proxy_url.rstrip('/')

            # 設定の保存
            with st.spinner(f"{selected_backend} のURL設定を保存中..."):
                try:
                    # バックエンド別の設定として保存
                    save_urls(selected_backend, target_url, proxy_url)
                    # セッション状態も更新
                    if "backend_urls" not in st.session_state:
                        st.session_state.backend_urls = {}
                    st.session_state.backend_urls[selected_backend] = {
                        "target_url": target_url,
                        "proxy_url": proxy_url
                    }
                    st.success(f"{selected_backend} のURL設定を保存しました")
                except Exception as e:
                    st.error(f"URL設定の保存に失敗しました: {str(e)}")