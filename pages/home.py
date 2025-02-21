import streamlit as st
import json
from utils.api_utils import send_request, is_valid_proxy_url, create_json_data, display_response
from utils.db_utils import save_post_data, load_post_data, delete_post_data, save_request, get_saved_post_data_names

def load_saved_data():
    selected_data = st.session_state.get("selected_data", "")
    if selected_data:
        data = load_post_data(selected_data)
        if data:
            # Update session state with loaded data
            st.session_state.update(data)
            return True
    return False

def show():
    st.title("Web Request Manager")

    # Load saved data if selected
    load_saved_data()

    # Proxy settings
    st.sidebar.header("Proxy Settings")
    st.session_state["proxy_url"] = st.sidebar.text_input(
        "Proxy URL (Optional)",
        value=st.session_state.get("proxy_url", "")
    )
    if st.session_state.proxy_url and not is_valid_proxy_url(st.session_state.proxy_url):
        st.sidebar.error("Invalid proxy URL format")

    # Target URL
    st.sidebar.header("Target Settings")
    st.session_state["target_url"] = st.sidebar.text_input(
        "Target URL",
        value=st.session_state.get("target_url", "")
    )

    # Main content
    st.header("Request Input")

    # POST data input
    col1, col2 = st.columns([2, 1])

    with col2:
        st.subheader("Saved POST Data")
        saved_data = get_saved_post_data_names()

        # Selectbox for loading saved data
        st.selectbox(
            "Load Saved Data",
            [""] + saved_data,
            key="selected_data"
        )

        save_name = st.text_input("Save as", key="save_name")
        if st.button("Save POST Data"):
            if save_name:
                current_data = create_json_data()
                save_post_data(save_name, current_data)
                st.success(f"Saved as {save_name}")
            else:
                st.error("Please enter a name to save")

        if st.button("Delete Selected"):
            if st.session_state.selected_data:
                delete_post_data(st.session_state.selected_data)
                st.success(f"Deleted {st.session_state.selected_data}")
                st.session_state.selected_data = ""
                st.experimental_rerun()

    with col1:
        st.session_state["question"] = st.text_area(
            "Question (Required)",
            value=st.session_state.get("question", "")
        )

        st.subheader("Overrides")
        st.session_state["retrieval_mode"] = st.selectbox(
            "Retrieval Mode",
            ["hybrid", "vectors", "text"],
            index=["hybrid", "vectors", "text"].index(st.session_state.get("retrieval_mode", "hybrid"))
        )

        col_a, col_b = st.columns(2)
        with col_a:
            st.session_state["semantic_ranker"] = st.checkbox(
                "Semantic Ranker",
                value=st.session_state.get("semantic_ranker", False)
            )
            st.session_state["semantic_captions"] = st.checkbox(
                "Semantic Captions",
                value=st.session_state.get("semantic_captions", False)
            )

        with col_b:
            st.session_state["top"] = st.number_input(
                "Top Results",
                min_value=1,
                max_value=50,
                value=st.session_state.get("top", 3)
            )
            st.session_state["temperature"] = st.number_input(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.get("temperature", 0.3),
                step=0.1
            )

        st.session_state["prompt_template"] = st.text_area(
            "Prompt Template",
            value=st.session_state.get("prompt_template", "")
        )
        st.session_state["exclude_category"] = st.text_input(
            "Exclude Category",
            value=st.session_state.get("exclude_category", "")
        )

    # Send request
    if st.button("Send Request", type="primary"):
        if not st.session_state.question:
            st.error("Question is required")
            return

        if not st.session_state.target_url:
            st.error("Target URL is required")
            return

        post_data = create_json_data()
        response = send_request(
            st.session_state.target_url,
            post_data,
            st.session_state.proxy_url if st.session_state.proxy_url else None
        )

        if response:
            display_response(response)
            # Save request to database
            save_request(
                target_url=st.session_state.target_url,
                post_data=json.dumps(post_data),
                response=json.dumps(response) if isinstance(response, dict) else response,
                proxy_url=st.session_state.proxy_url
            )