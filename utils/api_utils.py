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

        # Add styles
        st.markdown("""
        <style>
        .data-points-container {
            margin-top: 1rem;
            margin-bottom: 2rem;
        }
        .copy-all-button {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
            margin-bottom: 1rem;
            color: #212529;
        }
        .copy-all-button:hover {
            background-color: #e9ecef;
        }
        .data-point {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 1rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
        }
        .data-point-content {
            flex: 1;
            margin: 0;
            word-break: break-word;
            line-height: 1.5;
        }
        .copy-button {
            background: none;
            border: none;
            padding: 0.25rem;
            cursor: pointer;
            color: #6c757d;
            line-height: 1;
            font-size: 1rem;
        }
        .copy-button:hover {
            color: #0d6efd;
        }
        #copyNotification {
            position: fixed;
            top: 1rem;
            right: 1rem;
            background-color: #198754;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            z-index: 1000;
            display: none;
            opacity: 0;
            transition: opacity 0.3s ease-in-out;
        }
        </style>
        """, unsafe_allow_html=True)

        # Notification element
        st.markdown("""
        <div id="copyNotification">コピーしました！</div>
        """, unsafe_allow_html=True)

        # JavaScript for copy functionality
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

        function copyToClipboard(text) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text)
                    .then(() => showNotification())
                    .catch(() => fallbackCopyToClipboard(text));
            } else {
                fallbackCopyToClipboard(text);
            }
        }

        function fallbackCopyToClipboard(text) {
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
                copyToClipboard(text);
            }
        });
        </script>
        """, unsafe_allow_html=True)

        # Create the data points container
        st.markdown('<div class="data-points-container">', unsafe_allow_html=True)

        # Copy all button
        all_points = "\n\n".join([f"{i+1}. {point}" for i, point in enumerate(response["data_points"])])
        escaped_all_points = html.escape(all_points)
        st.markdown(f"""
        <button class="copy-all-button" data-copy-text="{escaped_all_points}">
            📋 全てをコピー
        </button>
        """, unsafe_allow_html=True)

        # Individual data points
        for i, point in enumerate(response["data_points"], 1):
            escaped_text = html.escape(point)
            st.markdown(f"""
            <div class="data-point">
                <button class="copy-button" data-copy-text="{escaped_text}">📋</button>
                <p class="data-point-content">{i}. {escaped_text}</p>
            </div>
            """, unsafe_allow_html=True)

        # Close the container
        st.markdown('</div>', unsafe_allow_html=True)

    # Display raw content if present
    if "content" in response:
        st.subheader("レスポンス内容")
        st.text(response["content"])

def escape_js_string(s):
    """Escape string for use in JavaScript"""
    return json.dumps(s)[1:-1]  # Remove the surrounding quotes