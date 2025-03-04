import streamlit as st
from typing import Dict, Any, List
from . import ChatBackend
from ..api_utils import make_request
import json

class OpenAIBackend(ChatBackend):
    """OpenAI backend implementation"""
    
    def get_name(self) -> str:
        return "OpenAI"
    
    def get_description(self) -> str:
        return "Direct OpenAI chat completion API integration"
    
    def get_settings_schema(self) -> Dict[str, Any]:
        return {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "system_prompt": "You are a helpful assistant.",
            "language": "ja"
        }
    
    def render_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Render settings UI specific to OpenAI backend"""
        settings = settings.copy()
        
        # Model selection
        settings["model"] = st.selectbox(
            "モデル",
            ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"],
            index=["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo"].index(settings["model"])
        )
        
        # System prompt
        settings["system_prompt"] = st.text_area(
            "システムプロンプト",
            settings["system_prompt"],
            help="AIアシスタントの役割や制約を定義します"
        )
        
        # Generation parameters
        settings["temperature"] = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=float(settings["temperature"]),
            step=0.1,
            help="生成される応答のランダム性を制御します。高いほど創造的で、低いほど一貫した応答になります。"
        )
        
        settings["max_tokens"] = st.number_input(
            "最大トークン数",
            min_value=100,
            max_value=4000,
            value=settings["max_tokens"],
            help="生成される応答の最大長を制御します"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            settings["frequency_penalty"] = st.slider(
                "頻出ペナルティ",
                min_value=-2.0,
                max_value=2.0,
                value=float(settings["frequency_penalty"]),
                step=0.1,
                help="同じ単語や表現の繰り返しを抑制します"
            )
        with col2:
            settings["presence_penalty"] = st.slider(
                "存在ペナルティ",
                min_value=-2.0,
                max_value=2.0,
                value=float(settings["presence_penalty"]),
                step=0.1,
                help="新しいトピックの導入を促進します"
            )
        
        return settings
    
    def handle_chat(self, messages: List[Dict[str, str]], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat interaction with OpenAI backend"""
        # Add system message if not present
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {
                "role": "system",
                "content": settings["system_prompt"]
            })
        
        payload = {
            "messages": messages,
            "model": settings["model"],
            "temperature": settings["temperature"],
            "max_tokens": settings["max_tokens"],
            "top_p": settings["top_p"],
            "frequency_penalty": settings["frequency_penalty"],
            "presence_penalty": settings["presence_penalty"]
        }
        
        response = make_request("POST", "/chat/openai", json.dumps(payload))
        
        if response and "error" not in response:
            return {
                "message": {
                    "role": "assistant",
                    "content": response["content"]
                },
                "context": {}  # OpenAI backend doesn't provide additional context
            }
        else:
            error_msg = response.get("error", "Unknown error occurred")
            raise Exception(f"Chat request failed: {error_msg}")