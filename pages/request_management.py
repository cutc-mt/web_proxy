import streamlit as st
import pandas as pd
import json
from utils.db_utils import load_requests_summary, delete_request, update_request_memo

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
        "data_points": "Data Points",
        "memo": "Memo"  # 新しいカラムを追加
    }

    selected_columns = st.multiselect(
        "Select columns to display",
        list(columns.keys()),
        default=["request_time", "request_name", "url", "status_code", "error", "memo"],  # デフォルトにmemoを追加
        format_func=lambda x: columns[x]
    )

    # Load requests
    requests = load_requests_summary()
    if requests is not None and not requests.empty:
        # Apply filter
        if filter_name:
            requests = requests[requests['request_name'].str.contains(filter_name, case=False, na=False)]

        # Display requests with memo editing
        st.write("リクエスト一覧（メモをクリックして編集できます）")

        # メモ編集用のフォーム
        with st.form("memo_edit_form"):
            edited_df = st.data_editor(
                requests[selected_columns],
                column_config={
                    "memo": st.column_config.TextColumn(
                        "Memo",
                        help="Click to edit memo",
                        width="large"
                    )
                },
                hide_index=True,
                key="requests_table"
            )

            if st.form_submit_button("Save Memos"):
                with st.spinner("メモを保存中..."):
                    # 変更されたメモを保存
                    for idx, row in edited_df.iterrows():
                        original_memo = requests.iloc[idx]["memo"]
                        if pd.isna(original_memo):
                            original_memo = ""
                        new_memo = row["memo"] if not pd.isna(row["memo"]) else ""

                        if original_memo != new_memo:
                            update_request_memo(row["request_name"], new_memo)

                    st.success("メモを保存しました")
                    st.experimental_rerun()

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