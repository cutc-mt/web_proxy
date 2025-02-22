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

        # Add styles for copy functionality
        st.markdown("""
        <style>
        .data-point-container {
            margin-bottom: 1rem;
        }
        .copy-all-button {
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            margin-bottom: 16px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .copy-all-button:hover {
            background-color: #e9ecef;
        }
        .data-point {
            display: flex;
            align-items: flex-start;
            padding: 12px;
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            margin-bottom: 8px;
        }
        .copy-button {
            background: none;
            border: none;
            cursor: pointer;
            padding: 4px;
            margin-right: 8px;
            color: #6c757d;
        }
        .copy-button:hover {
            color: #0d6efd;
        }
        .data-point-content {
            flex-grow: 1;
            word-break: break-word;
        }
        #copyNotification {
            position: fixed;
            top: 16px;
            right: 16px;
            background-color: #198754;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            z-index: 1000;
            display: none;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }
        </style>
        """, unsafe_allow_html=True)

        # Add notification element
        st.markdown("""
        <div id="copyNotification">コピーしました！</div>
        """, unsafe_allow_html=True)

        # Add JavaScript for copy functionality
        st.markdown("""
        <script>
        function showNotification() {
            const notification = document.getElementById('copyNotification');
            notification.style.display = 'block';
            notification.style.opacity = '1';
            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => {
                    notification.style.display = 'none';
                }, 300);
            }, 2000);
        }

        function copyText(text) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text)
                    .then(() => showNotification())
                    .catch(() => fallbackCopy(text));
            } else {
                fallbackCopy(text);
            }
        }

        function fallbackCopy(text) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                textArea.remove();
                showNotification();
            } catch (err) {
                console.error('Copy failed:', err);
                alert('コピーに失敗しました');
            }
        }

        document.addEventListener('click', function(event) {
            const button = event.target.closest('[data-copy-text]');
            if (button) {
                const text = button.getAttribute('data-copy-text');
                copyText(text);
            }
        });
        </script>
        """, unsafe_allow_html=True)

        # Create copy all button
        all_points = "\n\n".join([f"{i+1}. {point}" for i, point in enumerate(response["data_points"])])
        escaped_all_points = html.escape(all_points)

        st.markdown(f"""
        <div class="data-point-container">
            <button class="copy-all-button" data-copy-text="{escaped_all_points}">
                📋 全てをコピー
            </button>
        </div>
        """, unsafe_allow_html=True)

        # Display individual data points
        for i, point in enumerate(response["data_points"], 1):
            escaped_text = html.escape(point)
            st.markdown(f"""
            <div class="data-point">
                <button class="copy-button" data-copy-text="{escaped_text}">📋</button>
                <div class="data-point-content">{i}. {escaped_text}</div>
            </div>
            """, unsafe_allow_html=True)

    # Display raw content if present
    if "content" in response:
        st.subheader("レスポンス内容")
        st.text(response["content"])

def escape_js_string(s):
    """Escape string for use in JavaScript"""
    return json.dumps(s)[1:-1]  # Remove the surrounding quotes