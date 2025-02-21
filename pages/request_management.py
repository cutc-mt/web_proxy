import streamlit as st
import pandas as pd
import json
from utils.db_utils import load_requests_summary, delete_request

def show():
    st.title("Request Management")

    # Filter by request name
    filter_name = st.text_input("Filter by Request Name", key="filter_name")

    # Column selection
    st.subheader("Column Selection")
    columns = {
        "request_time": "Request Time",
        "request_name": "Request Name",
        "url": "URL",
        "status_code": "Status Code",
        "post_data_preview": "POST Data Preview",
        "error": "Error",
        "answer": "Answer",
        "thoughts": "Thoughts",
        "data_points": "Data Points"
    }
    
    selected_columns = st.multiselect(
        "Select columns to display",
        list(columns.keys()),
        default=["request_time", "request_name", "url", "status_code", "error"],
        format_func=lambda x: columns[x]
    )

    # Load requests
    requests = load_requests_summary()
    if requests is not None and not requests.empty:
        # Apply filter
        if filter_name:
            requests = requests[requests['request_name'].str.contains(filter_name, case=False, na=False)]

        # Display requests
        st.dataframe(requests[selected_columns])

        # Export to CSV
        if st.button("Export to CSV"):
            csv = requests.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="requests_export.csv",
                mime="text/csv"
            )

        # Delete requests
        st.subheader("Delete Requests")
        request_to_delete = st.selectbox(
            "Select request to delete",
            requests['request_name'].tolist(),
            key="request_to_delete"
        )
        
        if st.button("Delete Selected Request"):
            delete_request(request_to_delete)
            st.success(f"Deleted request: {request_to_delete}")
            st.experimental_rerun()
    else:
        st.info("No requests found")
