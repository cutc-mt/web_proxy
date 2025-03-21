import streamlit as st
from typing import Dict, Any, List
from . import ChatBackend
from ..api_utils import make_request
import json

class AzureOpenAIBackend(ChatBackend):
    """Azure OpenAI backend implementation"""
    
    def get_default_qa_settings(self) -> Dict[str, Any]:
        """デフォルトのQ&A設定を取得"""
        return {
            "retrieval_mode": "hybrid",
            "top": 3,
            "semantic_ranker": True,
            "semantic_captions": True,
            "temperature": 0.7,
            "exclude_category": "",
            "prompt_template": "",
            "include_category": "",
            "minimum_reranker_score": 0.0,
            "minimum_search_score": 0.0,
            "vector_fields": ["embedding"],
            "language": "ja"
        }
    
    def get_qa_settings(self) -> Dict[str, Any]:
        """現在のQ&A設定を取得"""
        defaults = self.get_default_qa_settings()
        settings = {}
        for key in defaults.keys():
            temp_key = f"_{key}"
            settings[key] = st.session_state.get(temp_key, st.session_state.get(key, defaults[key]))
        return settings
    
    def render_qa_settings(self) -> None:
        """Q&A設定のUIを表示"""
        # 検索設定
        modes = ["hybrid", "vectors", "text"]
        st.selectbox(
            "検索モード",
            modes,
            key="_retrieval_mode",
            index=modes.index(st.session_state.get("retrieval_mode", "hybrid"))
        )
        
        st.number_input(
            "参照件数",
            min_value=1,
            max_value=50,
            key="_top",
            value=st.session_state.get("top", 3)
        )
        
        # スコア設定
        col1, col2 = st.columns(2)
        with col1:
            st.number_input(
                "最小リランカースコア",
                min_value=0.0,
                max_value=1.0,
                key="_minimum_reranker_score",
                value=st.session_state.get("minimum_reranker_score", 0.0)
            )
        with col2:
            st.number_input(
                "最小検索スコア",
                min_value=0.0,
                max_value=1.0,
                key="_minimum_search_score",
                value=st.session_state.get("minimum_search_score", 0.0)
            )
        
        # 機能設定
        st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            step=0.1,
            key="_temperature",
            value=st.session_state.get("temperature", 0.7)
        )
        
        st.checkbox(
            "セマンティック検索",
            key="_semantic_ranker",
            value=st.session_state.get("semantic_ranker", True)
        )
        
        st.checkbox(
            "セマンティックキャプション",
            key="_semantic_captions",
            value=st.session_state.get("semantic_captions", True)
        )
        
        # フィルター設定
        st.text_area(
            "除外カテゴリ（カンマ区切り）",
            key="_exclude_category",
            value=st.session_state.get("exclude_category", "")
        )
        
        st.text_area(
            "含めるカテゴリ（カンマ区切り）",
            key="_include_category",
            value=st.session_state.get("include_category", "")
        )
        
        st.text_area(
            "プロンプトテンプレート",
            key="_prompt_template",
            value=st.session_state.get("prompt_template", "")
        )
    
    def serialize_qa_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Q&A設定をシリアライズ"""
        return {
            "messages": [],  # Q&Aモードでは空の履歴
            "context": {
                "overrides": {
                    "retrieval_mode": str(settings["retrieval_mode"]),
                    "semantic_ranker": bool(settings["semantic_ranker"]),
                    "semantic_captions": bool(settings["semantic_captions"]),
                    "top": int(settings["top"]),
                    "temperature": float(settings["temperature"]),
                    "prompt_template": str(settings["prompt_template"]),
                    "exclude_category": str(settings["exclude_category"]),
                    "include_category": str(settings["include_category"]),
                    "minimum_reranker_score": float(settings["minimum_reranker_score"]),
                    "minimum_search_score": float(settings["minimum_search_score"]),
                    "vector_fields": settings.get("vector_fields", ["embedding"]),
                    "language": settings.get("language", "ja")
                }
            }
        }
    
    def deserialize_qa_settings(self, data: Dict[str, Any]) -> None:
        """Q&A設定をデシリアライズして適用"""
        if isinstance(data, dict):
            if "context" in data and "overrides" in data["context"]:
                data = data["context"]["overrides"]
            for key, value in data.items():
                st.session_state[key] = value
                st.session_state[f"_{key}"] = value
    
    def create_qa_request(self, question: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Q&Aリクエストペイロードを作成"""
        return {
            "messages": [{"role": "user", "content": question}],
            "context": {
                "overrides": {
                    "retrieval_mode": str(settings["retrieval_mode"]),
                    "semantic_ranker": bool(settings["semantic_ranker"]),
                    "semantic_captions": bool(settings["semantic_captions"]),
                    "top": int(settings["top"]),
                    "temperature": float(settings["temperature"]),
                    "prompt_template": str(settings.get("prompt_template", "")),
                    "exclude_category": str(settings.get("exclude_category", "")),
                    "include_category": str(settings.get("include_category", "")),
                    "minimum_reranker_score": float(settings.get("minimum_reranker_score", 0.0)),
                    "minimum_search_score": float(settings.get("minimum_search_score", 0.0)),
                    "vector_fields": settings.get("vector_fields", ["embedding"]),
                    "language": settings.get("language", "ja")
                }
            }
        }
    
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