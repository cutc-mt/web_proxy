import streamlit as st
from typing import Dict, Any, List
from . import ChatBackend
from ..api_utils import make_request
import json

class AzureOpenAILegacyBackend(ChatBackend):
    """Azure OpenAI Legacy backend implementation"""
    
    def get_default_qa_settings(self) -> Dict[str, Any]:
        """デフォルトのQ&A設定を取得"""
        return {
            "retrieval_mode": "hybrid",
            "top": 3,
            "semantic_ranker": True,
            "semantic_captions": False,
            "temperature": 0.3,
            "exclude_category": "",
            "prompt_template": ""
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
        
        # 機能設定
        st.checkbox(
            "セマンティック検索",
            key="_semantic_ranker",
            value=st.session_state.get("semantic_ranker", True)
        )
        
        st.checkbox(
            "セマンティックキャプション",
            key="_semantic_captions",
            value=st.session_state.get("semantic_captions", False)
        )
        
        st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            step=0.1,
            key="_temperature",
            value=st.session_state.get("temperature", 0.3)
        )
        
        st.text_area(
            "除外カテゴリ（カンマ区切り）",
            key="_exclude_category",
            value=st.session_state.get("exclude_category", "")
        )
        
        st.text_area(
            "プロンプトテンプレート",
            key="_prompt_template",
            value=st.session_state.get("prompt_template", "")
        )
    
    def serialize_qa_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Q&A設定をシリアライズ"""
        return {
            "approach": "rtr",
            "overrides": {
                "retrieval_mode": str(settings["retrieval_mode"]),
                "semantic_ranker": bool(settings["semantic_ranker"]),
                "semantic_captions": bool(settings["semantic_captions"]),
                "top": int(settings["top"]),
                "temperature": float(settings["temperature"]),
                "prompt_template": str(settings["prompt_template"]),
                "exclude_category": str(settings["exclude_category"])
            }
        }
    
    def deserialize_qa_settings(self, data: Dict[str, Any]) -> None:
        """Q&A設定をデシリアライズして適用"""
        if isinstance(data, dict):
            if "overrides" in data:
                data = data["overrides"]
            for key, value in data.items():
                st.session_state[key] = value
                st.session_state[f"_{key}"] = value
    
    def create_qa_request(self, question: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Q&Aリクエストペイロードを作成"""
        return {
            "question": question,
            "approach": "rtr",
            "overrides": {
                "retrieval_mode": str(settings["retrieval_mode"]),
                "semantic_ranker": bool(settings["semantic_ranker"]),
                "semantic_captions": bool(settings["semantic_captions"]),
                "top": int(settings["top"]),
                "temperature": float(settings["temperature"]),
                "prompt_template": str(settings.get("prompt_template", "")),
                "exclude_category": str(settings.get("exclude_category", ""))
            }
        }
    
    def get_name(self) -> str:
        return "Azure OpenAI (Legacy)"
    
    def get_description(self) -> str:
        return "旧バージョンのAzure OpenAI チャットバックエンド"
    
    def get_settings_schema(self) -> Dict[str, Any]:
        return {
            "retrieval_mode": "hybrid",
            "semantic_captions": True,
            "top": 5,
            "exclude_category": "",
            "semantic_ranker": True,
            "suggest_followup_questions": True,
            "prompt_override": "",
            "temperature": 0.3,
        }
    
    def render_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Render settings UI specific to Azure OpenAI Legacy backend"""
        settings = settings.copy()
        
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
            value=int(settings["top"])
        )
        
        # Feature settings
        settings["temperature"] = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=float(settings["temperature"]),
            step=0.1,
            help="生成される応答のランダム性を制御します"
        )
        
        settings["semantic_ranker"] = st.checkbox(
            "セマンティックランカーを使用",
            bool(settings["semantic_ranker"])
        )
        
        settings["semantic_captions"] = st.checkbox(
            "セマンティックキャプションを使用",
            bool(settings["semantic_captions"])
        )
        
        settings["suggest_followup_questions"] = st.checkbox(
            "フォローアップ質問を提案",
            bool(settings["suggest_followup_questions"])
        )
        
        settings["exclude_category"] = st.text_input(
            "除外カテゴリ",
            settings["exclude_category"]
        )
        
        settings["prompt_override"] = st.text_area(
            "プロンプトオーバーライド",
            settings["prompt_override"]
        )
        
        return settings
    
    def handle_chat(self, messages: List[Dict[str, str]], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat interaction with Azure OpenAI Legacy backend"""
        # Format legacy request
        payload = {
            "approach": "rrr",  # 固定値
            "history": [{"user": msg["content"]} if msg["role"] == "user" else {"assistant": msg["content"]} for msg in messages],
            "overrides": {
                "retrieval_mode": settings["retrieval_mode"],
                "semantic_captions": bool(settings["semantic_captions"]),
                "top": int(settings["top"]),
                "exclude_category": settings["exclude_category"],
                "semantic_ranker": bool(settings["semantic_ranker"]),
                "suggest_followup_questions": bool(settings["suggest_followup_questions"]),
                "prompt_override": settings["prompt_override"],
                "temperature": float(settings["temperature"])
            }
        }
        
        # Debug output for request
        st.write("Legacy Backend Request:", json.dumps(payload, indent=2, ensure_ascii=False))
        
        response = make_request("POST", "/chat", json.dumps(payload))
        
        # Debug output for response
        st.write("Legacy Backend Response:", json.dumps(response, indent=2, ensure_ascii=False))
        
        if response and "error" not in response:
            # Convert legacy response format to new format
            return {
                "message": {
                    "role": "assistant",
                    "content": response["answer"]
                },
                "context": {
                    "data_points": response["data_points"] if isinstance(response["data_points"], list) else [response["data_points"]] if response["data_points"] else [],
                    "thoughts": response["thoughts"] if response["thoughts"] else ""
                }
            }
        else:
            error_msg = response.get("error", "Unknown error occurred")
            raise Exception(f"Chat request failed: {error_msg}")