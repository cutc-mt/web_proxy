import streamlit as st
import json
from utils.api_utils import send_request, is_valid_proxy_url, create_json_data, display_response
from utils.db_utils import save_post_data, load_post_data, delete_post_data, save_request, get_saved_post_data_names

def initialize_session_state():
    defaults = {
        "proxy_url": "",
        "target_url": "",
        "question": "",
        "retrieval_mode": "hybrid",
        "semantic_ranker": False,
        "semantic_captions": False,
        "top": 3,
        "temperature": 0.3,
        "prompt_template": "",
        "exclude_category": "",
        "selected_data": "",
        "save_name": "",
        "form_submitted": False  # 追加: フォーム送信フラグ
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_form():
    # Reset all form fields to default values
    defaults = {
        "question": "",
        "retrieval_mode": "hybrid",
        "semantic_ranker": False,
        "semantic_captions": False,
        "top": 3,
        "temperature": 0.3,
        "prompt_template": "",
        "exclude_category": "",
        "selected_data": "",
        "save_name": "",
        "form_submitted": True  # フォーム送信フラグを設定
    }

    for key, value in defaults.items():
        st.session_state[key] = value

def load_saved_data(name):
    if name:
        data = load_post_data(name)
        if data:
            # Update question
            if "question" in data:
                st.session_state.question = data["question"]

            # Update overrides
            if "overrides" in data:
                overrides = data["overrides"]
                st.session_state.retrieval_mode = overrides.get("retrieval_mode", "hybrid")
                st.session_state.semantic_ranker = overrides.get("semantic_ranker", False)
                st.session_state.semantic_captions = overrides.get("semantic_captions", False)
                st.session_state.top = overrides.get("top", 3)
                st.session_state.temperature = overrides.get("temperature", 0.3)
                st.session_state.prompt_template = overrides.get("prompt_template", "")
                st.session_state.exclude_category = overrides.get("exclude_category", "")
            return True
    return False

def show():
    st.title("Web Request Manager")

    # Initialize session state
    initialize_session_state()

    # Proxy settings
    st.sidebar.header("Proxy Settings")
    proxy_url = st.sidebar.text_input(
        "Proxy URL (Optional)",
        value=st.session_state.proxy_url,
        key="proxy_url_input"
    )
    if proxy_url and not is_valid_proxy_url(proxy_url):
        st.sidebar.error("Invalid proxy URL format")
    st.session_state.proxy_url = proxy_url

    # Target URL
    st.sidebar.header("Target Settings")
    target_url = st.sidebar.text_input(
        "Target URL",
        value=st.session_state.target_url,
        key="target_url_input"
    )
    st.session_state.target_url = target_url

    # Main content
    st.header("Request Input")

    # POST data input
    col1, col2 = st.columns([2, 1])

    with col2:
        st.subheader("Saved POST Data")
        saved_data = get_saved_post_data_names()

        # Selectbox for loading saved data
        selected_data = st.selectbox(
            "Load Saved Data",
            [""] + saved_data,
            key="selected_data_input"
        )

        # Load data when selection changes
        if selected_data != st.session_state.selected_data:
            st.session_state.selected_data = selected_data
            if selected_data:
                load_saved_data(selected_data)
                st.rerun()

        # フォームが送信された後は空の値を表示
        initial_value = "" if st.session_state.form_submitted else st.session_state.get("save_name_input", "")
        save_name = st.text_input("Save as", value=initial_value, key="save_name_input")
        if st.button("Save POST Data"):
            if save_name:
                current_data = {
                    "question": st.session_state.question,
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
                save_post_data(save_name, current_data)
                st.success(f"Saved as {save_name}")
                # Reset form after successful save
                reset_form()
                st.rerun()
            else:
                st.error("Please enter a name to save")

        if st.button("Delete Selected"):
            if selected_data:
                delete_post_data(selected_data)
                st.success(f"Deleted {selected_data}")
                st.session_state.selected_data = ""
                st.rerun()

    # フォーム送信フラグをリセット
    if st.session_state.form_submitted:
        st.session_state.form_submitted = False

    with col1:
        st.text_area(
            "Question (Required)",
            value=st.session_state.question,
            key="question_input",
            on_change=lambda: setattr(st.session_state, "question", st.session_state.question_input)
        )

        st.subheader("Overrides")
        st.selectbox(
            "Retrieval Mode",
            ["hybrid", "vectors", "text"],
            index=["hybrid", "vectors", "text"].index(st.session_state.retrieval_mode),
            key="retrieval_mode_input",
            on_change=lambda: setattr(st.session_state, "retrieval_mode", st.session_state.retrieval_mode_input)
        )

        col_a, col_b = st.columns(2)
        with col_a:
            st.checkbox(
                "Semantic Ranker",
                value=st.session_state.semantic_ranker,
                key="semantic_ranker_input",
                on_change=lambda: setattr(st.session_state, "semantic_ranker", st.session_state.semantic_ranker_input)
            )

            st.checkbox(
                "Semantic Captions",
                value=st.session_state.semantic_captions,
                key="semantic_captions_input",
                on_change=lambda: setattr(st.session_state, "semantic_captions", st.session_state.semantic_captions_input)
            )

        with col_b:
            st.number_input(
                "Top Results",
                min_value=1,
                max_value=50,
                value=st.session_state.top,
                key="top_input",
                on_change=lambda: setattr(st.session_state, "top", st.session_state.top_input)
            )

            st.number_input(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.temperature,
                step=0.1,
                key="temperature_input",
                on_change=lambda: setattr(st.session_state, "temperature", st.session_state.temperature_input)
            )

        st.text_area(
            "Prompt Template",
            value=st.session_state.prompt_template,
            key="prompt_template_input",
            on_change=lambda: setattr(st.session_state, "prompt_template", st.session_state.prompt_template_input)
        )

        st.text_input(
            "Exclude Category",
            value=st.session_state.exclude_category,
            key="exclude_category_input",
            on_change=lambda: setattr(st.session_state, "exclude_category", st.session_state.exclude_category_input)
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