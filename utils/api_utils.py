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

    # Display status code
    st.subheader("ステータスコード")
    st.write(response.get("status_code", "N/A"))

    # Display headers
    if "headers" in response:
        st.subheader("ヘッダー")
        st.json(response["headers"])

    # Display error if present
    if "error" in response and response["error"]:
        st.error(f"エラー: {response['error']}")
        return

    # Display answer, thoughts, and data points if present
    if "answer" in response:
        st.subheader("回答")
        st.write(response["answer"])

    if "thoughts" in response:
        st.subheader("思考プロセス")
        st.write(response["thoughts"])

    if "data_points" in response:
        st.subheader("データポイント")
        for point in response["data_points"]:
            st.write(f"- {point}")

    # If response is not JSON formatted
    if "content" in response:
        st.subheader("レスポンス内容")
        st.text(response["content"])