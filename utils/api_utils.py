import requests
import json
import streamlit as st
from urllib.parse import urlparse

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

        # Add copy functionality CSS and JavaScript
        st.markdown("""
        <style>
        .data-point-card {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
            border: 1px solid #e0e0e0;
            position: relative;
        }
        .copy-button {
            position: absolute;
            top: 10px;
            right: 10px;
            background: none;
            border: none;
            cursor: pointer;
            padding: 5px;
            color: #666;
        }
        .copy-button:hover {
            color: #000;
        }
        .copy-all-button {
            margin-bottom: 10px;
            background: none;
            border: 1px solid #e0e0e0;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .copy-all-button:hover {
            background-color: #f5f5f5;
        }
        @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css');
        </style>
        <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                // Show success message
                const tooltip = document.createElement('div');
                tooltip.textContent = 'コピーしました！';
                tooltip.style.position = 'fixed';
                tooltip.style.padding = '8px';
                tooltip.style.background = '#4CAF50';
                tooltip.style.color = 'white';
                tooltip.style.borderRadius = '4px';
                tooltip.style.zIndex = '1000';
                tooltip.style.top = '20px';
                tooltip.style.right = '20px';
                document.body.appendChild(tooltip);
                setTimeout(() => tooltip.remove(), 2000);
            });
        }
        </script>
        """, unsafe_allow_html=True)

        # Create copy all button
        all_points = "\n\n".join([f"{i+1}. {point}" for i, point in enumerate(response["data_points"])])
        st.markdown(f"""
        <button class="copy-all-button" onclick="copyToClipboard(`{all_points}`)">
            <i class="fas fa-copy"></i> 全てをコピー
        </button>
        """, unsafe_allow_html=True)

        # Display individual data points with copy buttons
        for i, point in enumerate(response["data_points"], 1):
            with st.container():
                st.markdown(f"""
                <div class="data-point-card">
                    <button class="copy-button" onclick="copyToClipboard(`{point}`)">
                        <i class="fas fa-copy"></i>
                    </button>
                    <p>{i}. {point}</p>
                </div>
                """, unsafe_allow_html=True)

    # If response is not JSON formatted
    if "content" in response:
        st.subheader("レスポンス内容")
        st.text(response["content"])