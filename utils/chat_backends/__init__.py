from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class ChatBackend(ABC):
    """Base class for chat backend implementations"""
    
    @abstractmethod
    def get_settings_schema(self) -> Dict[str, Any]:
        """Return the schema for backend-specific settings"""
        pass
    
    @abstractmethod
    def render_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Render backend-specific settings UI and return updated settings"""
        pass
    
    @abstractmethod
    def handle_chat(self, messages: List[Dict[str, str]], settings: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat interaction with the backend"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the display name of this backend"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a description of this backend"""
        pass
    
    @abstractmethod
    def get_default_qa_settings(self) -> Dict[str, Any]:
        """Get default settings for Q&A"""
        pass
    
    @abstractmethod
    def get_qa_settings(self) -> Dict[str, Any]:
        """Get current Q&A settings from session state"""
        pass
    
    @abstractmethod
    def render_qa_settings(self) -> None:
        """Render Q&A settings UI widgets"""
        pass
    
    @abstractmethod
    def serialize_qa_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize Q&A settings for storage"""
        pass
    
    @abstractmethod
    def deserialize_qa_settings(self, data: Dict[str, Any]) -> None:
        """Deserialize and apply stored Q&A settings"""
        pass
    
    @abstractmethod
    def create_qa_request(self, question: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Create Q&A request payload"""
        pass