from typing import Dict, Type, Optional
from . import ChatBackend
from .azure_openai import AzureOpenAIBackend
from .azure_openai_legacy import AzureOpenAILegacyBackend

class ChatBackendManager:
    """Manages available chat backends and their instances"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChatBackendManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the backend registry"""
        self._backends: Dict[str, Type[ChatBackend]] = {}
        self._current_backend: Optional[ChatBackend] = None
        
        # Register default backends
        self.register_backend("azure_openai_legacy", AzureOpenAILegacyBackend)
        self.register_backend("azure_openai", AzureOpenAIBackend)
        
        # Set default backend
        self.set_current_backend("azure_openai_legacy")
    
    def register_backend(self, backend_id: str, backend_class: Type[ChatBackend]):
        """Register a new backend class"""
        self._backends[backend_id] = backend_class
    
    def get_available_backends(self) -> Dict[str, Type[ChatBackend]]:
        """Get all registered backends"""
        return self._backends
    
    def create_backend(self, backend_id: str) -> ChatBackend:
        """Create an instance of a backend"""
        if backend_id not in self._backends:
            raise ValueError(f"Unknown backend: {backend_id}")
        return self._backends[backend_id]()
    
    def set_current_backend(self, backend_id: str):
        """Set the current active backend"""
        self._current_backend = self.create_backend(backend_id)
    
    def get_current_backend(self) -> Optional[ChatBackend]:
        """Get the currently active backend"""
        return self._current_backend