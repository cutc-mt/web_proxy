import streamlit as st
import json
from utils.api_utils import send_request, is_valid_proxy_url, create_json_data, display_response
from utils.db_utils import save_post_data, load_post_data, delete_post_data, save_request, get_saved_post_data_names

def show():
    st.title("Web Request Manager")

    # Proxy settings
    st.sidebar.header("Proxy Settings")
    proxy_url = st.sidebar.text_input("Proxy URL (Optional)", key="proxy_url")
    if proxy_url and not is_valid_proxy_url(proxy_url):
        st.sidebar.error("Invalid proxy URL format")

    # Target URL
    st.sidebar.header("Target Settings")
    target_url = st.sidebar.text_input("Target URL", key="target_url")

    # Main content
    st.header("Request Input")
    
    # POST data input
    col1, col2 = st.columns([2, 1])
    
    with col1:
        question = st.text_area("Question (Required)", key="question")
        
        st.subheader("Overrides")
        retrieval_mode = st.selectbox(
            "Retrieval Mode",
            ["hybrid", "vectors", "text"],
            key="retrieval_mode"
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            semantic_ranker = st.checkbox("Semantic Ranker", key="semantic_ranker")
            semantic_captions = st.checkbox("Semantic Captions", key="semantic_captions")
        
        with col_b:
            top = st.number_input("Top Results", min_value=1, max_value=50, value=3, key="top")
            temperature = st.number_input("Temperature", min_value=0.0, max_value=1.0, value=0.3, step=0.1, key="temperature")
        
        prompt_template = st.text_area("Prompt Template", key="prompt_template")
        exclude_category = st.text_input("Exclude Category", key="exclude_category")

    with col2:
        st.subheader("Saved POST Data")
        saved_data = get_saved_post_data_names()
        
        selected_data = st.selectbox("Load Saved Data", [""] + saved_data, key="selected_data")
        if selected_data:
            data = load_post_data(selected_data)
            if data:
                for key, value in data.items():
                    if key in st.session_state:
                        st.session_state[key] = value

        save_name = st.text_input("Save as", key="save_name")
        if st.button("Save POST Data"):
            if save_name:
                current_data = create_json_data()
                save_post_data(save_name, current_data)
                st.success(f"Saved as {save_name}")
            else:
                st.error("Please enter a name to save")

        if st.button("Delete Selected"):
            if selected_data:
                delete_post_data(selected_data)
                st.success(f"Deleted {selected_data}")
                st.session_state.selected_data = ""

    # Send request
    if st.button("Send Request", type="primary"):
        if not question:
            st.error("Question is required")
            return
        
        if not target_url:
            st.error("Target URL is required")
            return

        post_data = create_json_data()
        response = send_request(target_url, post_data, proxy_url if proxy_url else None)
        
        if response:
            display_response(response)
            # Save request to database
            save_request(
                target_url=target_url,
                post_data=json.dumps(post_data),
                response=json.dumps(response) if isinstance(response, dict) else response,
                proxy_url=proxy_url
            )
