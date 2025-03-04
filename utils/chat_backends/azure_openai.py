import streamlit as st
from typing import Dict, Any, List
from . import ChatBackend
from ..api_utils import make_request
import json

class AzureOpenAIBackend(ChatBackend):
    """Azure OpenAI backend implementation"""
    
    def get_name(self) -> str:
        return "Azure OpenAI"
    
    def get_description(self) -> str:
        return "Azure OpenAI based chat backend with document search capabilities"
    
    def get_settings_schema(self) -> Dict[str, Any]:
        return {
            "prompt_template": "",
            "include_category": "",
            "exclude_category": "",
            "top": 3,
            "temperature": 0.7,
            "minimum_reranker_score": 0.0,
            "minimum_search_score": 0.0,
            "retrieval_mode": "hybrid",
            "semantic_ranker": True,
            "semantic_captions": True,
            "suggest_followup_questions": True,
            "use_oid_security_filter": False,
            "use_groups_security_filter": False,
            "vector_fields": ["embedding"],
            "use_gpt4v": False,
            "gpt4v_input": "text",
            "language": "ja"
        }
    
    def render_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Render settings UI specific to Azure OpenAI backend"""
        settings = settings.copy()
        
        # Basic settings
        settings["prompt_template"] = st.text_area(
            "プロンプトテンプレート", 
            settings["prompt_template"]
        )
        
        # Search settings
        settings["retrieval_mode"] = st.selectbox(
            "検索モード",
            ["hybrid", "text", "vectors"],
            index=["hybrid", "text", "vectors"].index(settings["retrieval_mode"])
        )
        
        settings["top"] = st.number_input(
            "取得件数",
            min_value=1,
            max_value=10,
            value=settings["top"]
        )
        
        # Score settings
        col1, col2 = st.columns(2)
        with col1:
            settings["minimum_reranker_score"] = st.number_input(
                "最小リランカースコア",
                min_value=0.0,
                max_value=1.0,
                value=float(settings["minimum_reranker_score"])
            )
        with col2:
            settings["minimum_search_score"] = st.number_input(
                "最小検索スコア",
                min_value=0.0,
                max_value=1.0,
                value=float(settings["minimum_search_score"])
            )
        
        # Feature settings
        settings["temperature"] = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=float(settings["temperature"]),
            step=0.1,
            help="生成される応答のランダム性を制御します。高いほど創造的で、低いほど一貫した応答になります。"
        )
        
        settings["semantic_ranker"] = st.checkbox(
            "セマンティックランカーを使用",
            settings["semantic_ranker"]
        )
        settings["semantic_captions"] = st.checkbox(
            "セマンティックキャプションを使用",
            settings["semantic_captions"]
        )
        settings["suggest_followup_questions"] = st.checkbox(
            "フォローアップ質問を提案",
            settings["suggest_followup_questions"]
        )
        
        return settings
    
    def handle_chat(self, messages: List[Dict[str, str]], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat interaction with Azure OpenAI backend"""
        payload = {
            "messages": messages,
            "context": {
                "overrides": settings
            },
            "session_state": st.session_state.get("current_session_state", "")
        }
        
        response = make_request("POST", "/chat", json.dumps(payload))
        
        if response and "error" not in response:
            # Update session state if provided
            if "session_state" in response:
                st.session_state.current_session_state = response["session_state"]
            
            return response
        else:
            error_msg = response.get("error", "Unknown error occurred")
            raise Exception(f"Chat request failed: {error_msg}")