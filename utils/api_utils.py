import requests
import json
import streamlit as st
from urllib.parse import urlparse
import html
import pyperclip

def is_valid_proxy_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def create_json_data():
    return {
        "question": st.session_state.question,
        "approach": "rtr",
        "overrides": {
            "retrieval_mode": st.session_state.retrieval_mode,
            "semantic_ranker": st.session_state.semantic_ranker,
            "semantic_captions": st.session_state.semantic_captions,
            "top": st.session_state.top,
            "temperature": st.session_state.temperature,
            "prompt_template": st.session_state.prompt_template,
            "exclude_category": st.session_state.exclude_category
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

def copy_to_clipboard(text):
    """クリップボードにテキストをコピーする"""
    pyperclip.copy(text)

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

        # Create a container for all data points
        with st.container():
            # Add a "Copy All" button
            all_points = "\n\n".join([f"{i+1}. {point}" for i, point in enumerate(response["data_points"])])
            if st.button("📋 全てをコピー", key="copy_all"):
                copy_to_clipboard(all_points)
                st.toast("全てのデータポイントをコピーしました！")

            # Display individual data points
            for i, point in enumerate(response["data_points"], 1):
                with st.container():
                    col1, col2 = st.columns([0.1, 0.9])
                    with col1:
                        if st.button("📋", key=f"copy_button_{i}", help=f"データポイント {i} をコピー"):
                            copy_to_clipboard(point)
                            st.toast(f"データポイント {i} をコピーしました！")
                    with col2:
                        st.markdown(f"{i}. {point}")
                st.divider()

    # Display raw content if present
    if "content" in response:
        st.subheader("レスポンス内容")
        st.text(response["content"])

def escape_js_string(s):
    """Escape string for use in JavaScript"""
    return json.dumps(s)[1:-1]  # Remove the surrounding quotes