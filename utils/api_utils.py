import requests
import json
import streamlit as st
from urllib.parse import urlparse
import html

def is_valid_proxy_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def create_json_data():
    """POSTリクエスト用のJSONデータを作成する

    Returns:
        dict: リクエストに使用するJSONデータ

    Note:
        現在のロードカウントに基づいてウィジェットの値を取得
    """
    load_count = st.session_state.get("load_count", 0)
    current_key = lambda name: f"{name}_{load_count}"

    return {
        "question": st.session_state[current_key("question")],
        "approach": "rtr",
        "overrides": {
            "retrieval_mode": st.session_state[current_key("retrieval_mode")],
            "semantic_ranker": st.session_state[current_key("semantic_ranker")],
            "semantic_captions": st.session_state[current_key("semantic_captions")],
            "top": st.session_state[current_key("top")],
            "temperature": st.session_state[current_key("temperature")],
            "prompt_template": st.session_state[current_key("prompt_template")],
            "exclude_category": st.session_state[current_key("exclude_category")]
        }
    }

def send_request(url, data, proxy_url=None):
    try:
        proxies = None
        if proxy_url:
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }

        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(
            url,
            json=data,
            proxies=proxies,
            headers=headers,
            timeout=30
        )

        response_data = {
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }

        try:
            response_data.update(response.json())
        except:
            response_data["content"] = response.text

        return response_data

    except Exception as e:
        return {
            "status_code": 0,
            "error": str(e)
        }

def display_response(response):
    st.header("レスポンス")

    # Display technical details in an expander
    with st.expander("技術詳細（ステータスコード・ヘッダー）", expanded=False):
        st.subheader("ステータスコード")
        st.write(response.get("status_code", "N/A"))

        if "headers" in response:
            st.subheader("ヘッダー")
            st.json(response["headers"])

    # Display error if present
    if "error" in response and response["error"]:
        st.error(f"エラー: {response['error']}")
        return

    # Display main response content
    if "answer" in response:
        st.subheader("回答")
        st.write(response["answer"])

    if "thoughts" in response:
        st.subheader("思考プロセス")
        st.write(response["thoughts"])

    if "data_points" in response:
        st.subheader("データポイント")

        # すべてのデータポイントを一つの文字列にまとめる
        all_points = "\n".join([f"{i+1}. {point}" for i, point in enumerate(response["data_points"], 1)])

        st.info("以下のテキストエリアから全てのデータポイントを選択してコピーできます")

        # 非表示のテキストエリアにデータを格納
        st.markdown("""
        <style>
        .stTextArea textarea {
            height: 0;
            opacity: 0;
            position: absolute;
        }
        </style>
        """, unsafe_allow_html=True)

        st.text_area("", value=all_points, key="copy_text")

        # データポイントを表示
        for i, point in enumerate(response["data_points"], 1):
            st.markdown(f"**{i}.** {point}")
            st.divider()

    # Display raw content if present
    if "content" in response:
        st.subheader("レスポンス内容")
        st.text(response["content"])

def escape_js_string(s):
    """Escape string for use in JavaScript"""
    return json.dumps(s)[1:-1]  # Remove the surrounding quotes

def make_request(method, endpoint, data=None):
    """
    汎用的なAPIリクエスト関数

    Args:
        method (str): HTTPメソッド（"GET", "POST"など）
        endpoint (str): APIエンドポイント（例: "/chat"）
        data (str, optional): JSON形式のリクエストボディ

    Returns:
        dict: レスポンスデータ
    """
    try:
        # APIのベースURLを取得（設定またはデフォルト値）
        base_url = st.session_state.get("api_base_url", "http://localhost:8000")
        
        # プロキシURLを取得
        proxy_url = st.session_state.get("proxy_url")
        
        # プロキシ設定
        proxies = None
        if proxy_url and is_valid_proxy_url(proxy_url):
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }

        # リクエストヘッダー
        headers = {
            "Content-Type": "application/json"
        }

        # 完全なURLを構築
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        # リクエストの実行
        response = requests.request(
            method=method.upper(),
            url=url,
            data=data,
            proxies=proxies,
            headers=headers,
            timeout=30
        )

        # レスポンスの解析
        try:
            return response.json()
        except json.JSONDecodeError:
            return {
                "error": f"JSONの解析に失敗しました: {response.text}"
            }

    except Exception as e:
        return {
            "error": f"リクエストエラー: {str(e)}"
        }