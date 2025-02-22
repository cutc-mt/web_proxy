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

def escape_js_string(s):
    """Escape string for use in JavaScript"""
    return json.dumps(s)[1:-1]  # Remove the surrounding quotes

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

        # Add copy button functionality
        st.markdown("""
        <style>
        .data-point {
            background-color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid #e0e0e0;
            margin-bottom: 1rem;
            position: relative;
        }
        .copy-button {
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            border: none;
            background: none;
            cursor: pointer;
            padding: 0.5rem;
            font-size: 1.2rem;
        }
        .copy-button:hover {
            color: #1E88E5;
        }
        .copy-all-button {
            display: inline-flex;
            align-items: center;
            padding: 0.5rem 1rem;
            margin-bottom: 1rem;
            background-color: white;
            border: 1px solid #e0e0e0;
            border-radius: 0.5rem;
            cursor: pointer;
            font-size: 1rem;
            gap: 0.5rem;
        }
        .copy-all-button:hover {
            background-color: #f5f5f5;
        }
        .copy-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #4CAF50;
            color: white;
            padding: 1rem;
            border-radius: 4px;
            z-index: 9999;
            display: none;
        }
        </style>

        <div id="copyNotification" class="copy-notification">コピーしました！</div>

        <script>
        function showNotification() {
            const notification = document.getElementById('copyNotification');
            notification.style.display = 'block';
            setTimeout(() => {
                notification.style.display = 'none';
            }, 2000);
        }

        async function copyToClipboard(text) {
            try {
                await navigator.clipboard.writeText(text);
                showNotification();
            } catch (err) {
                console.error('Failed to copy text:', err);
            }
        }
        </script>
        """, unsafe_allow_html=True)

        # Create "Copy All" button with escaped content
        all_points = "\n\n".join([f"{i+1}. {point}" for i, point in enumerate(response["data_points"])])
        escaped_all_points = escape_js_string(all_points)
        st.markdown(f"""
        <button class="copy-all-button" onclick="copyToClipboard('{escaped_all_points}')">
            📋 全てをコピー
        </button>
        """, unsafe_allow_html=True)

        # Display individual data points with escaped content
        for i, point in enumerate(response["data_points"], 1):
            escaped_point = escape_js_string(point)
            escaped_html = html.escape(point)
            st.markdown(f"""
            <div class="data-point">
                <button class="copy-button" onclick="copyToClipboard('{escaped_point}')">📋</button>
                <p>{i}. {escaped_html}</p>
            </div>
            """, unsafe_allow_html=True)

    # If response is not JSON formatted
    if "content" in response:
        st.subheader("レスポンス内容")
        st.text(response["content"])