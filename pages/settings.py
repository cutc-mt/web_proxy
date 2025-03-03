import streamlit as st
from utils.db_utils import save_last_used_urls, load_last_used_urls
from utils.api_utils import is_valid_proxy_url

def show():
    """設定ページの表示"""
    st.title("⚙️ 設定")
    
    # URL設定
    st.header("共通URL設定")
    
    # 保存されたURLを読み込む
    try:
        saved_urls = load_last_used_urls()
        initial_target_url = saved_urls.get("target_url", "")
        initial_proxy_url = saved_urls.get("proxy_url", "")
    except Exception as e:
        st.error(f"URL設定の読み込みに失敗しました: {str(e)}")
        initial_target_url = ""
        initial_proxy_url = ""
    
    with st.form("url_settings_form", clear_on_submit=False):
        st.markdown("""
        ℹ️ ターゲットURLはベースURLのみを入力してください。
        例: `https://api.example.com`
        """)
        
        # Target URLの入力フィールド
        target_url = st.text_input(
            "ターゲットURL",
            value=initial_target_url,
            help="APIのベースURLを入力してください（/chatや/askは不要）",
            placeholder="https://api.example.com"
        )

        # Proxy URLの入力フィールド
        proxy_url = st.text_input(
            "プロキシURL（オプション）",
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
                "設定を保存",
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
            with st.spinner("URL設定を保存中..."):
                try:
                    save_last_used_urls(target_url, proxy_url)
                    st.session_state.target_url = target_url
                    st.session_state.proxy_url = proxy_url
                    st.success("URL設定を保存しました")
                except Exception as e:
                    st.error(f"URL設定の保存に失敗しました: {str(e)}")