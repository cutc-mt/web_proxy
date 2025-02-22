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

        # Add copy button functionality
        st.markdown("""
        <style>
        .stButton>button {
            width: 100%;
            margin-bottom: 1rem;
        }
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
        }
        .copy-button:hover {
            color: #1E88E5;
        }
        </style>
        """, unsafe_allow_html=True)

        # Add JavaScript for copy functionality
        st.markdown("""
        <script>
        async function copyText(text) {
            try {
                await navigator.clipboard.writeText(text);
                // Show success message
                const div = document.createElement('div');
                div.style.position = 'fixed';
                div.style.top = '20px';
                div.style.right = '20px';
                div.style.backgroundColor = '#4CAF50';
                div.style.color = 'white';
                div.style.padding = '1rem';
                div.style.borderRadius = '4px';
                div.style.zIndex = '9999';
                div.textContent = 'コピーしました！';
                document.body.appendChild(div);
                setTimeout(() => div.remove(), 2000);
            } catch (err) {
                console.error('Failed to copy text: ', err);
            }
        }
        </script>
        """, unsafe_allow_html=True)

        # Create "Copy All" button
        all_points = "\n\n".join([f"{i+1}. {point}" for i, point in enumerate(response["data_points"])])
        st.button("📋 全てをコピー", on_click=lambda: st.write(f'<script>copyText(`{all_points}`)</script>', unsafe_allow_html=True))

        # Display individual data points
        for i, point in enumerate(response["data_points"], 1):
            st.markdown(f"""
            <div class="data-point">
                <button class="copy-button" onclick="copyText(`{point}`)">📋</button>
                <p>{i}. {point}</p>
            </div>
            """, unsafe_allow_html=True)

    # If response is not JSON formatted
    if "content" in response:
        st.subheader("レスポンス内容")
        st.text(response["content"])