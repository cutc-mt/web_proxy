# チャットバックエンドシステム

このディレクトリには、複数のチャットバックエンドを管理するためのシステムが含まれています。

## 概要

このシステムは以下のコンポーネントで構成されています：

- `ChatBackend` 基底クラス：全てのバックエンド実装の基礎となるインターフェース
- `ChatBackendManager`：バックエンドの登録と管理を行うシングルトンクラス
- 各種バックエンド実装（AzureOpenAI, OpenAI等）

## 既存のバックエンド

1. **Azure OpenAI Backend** (azure_openai.py)
   - Azure OpenAIベースのチャットシステム
   - ドキュメント検索機能付き
   - セマンティック検索、リランキング機能対応

2. **OpenAI Backend** (openai.py)
   - 標準的なOpenAI Chat Completion API
   - GPT-4、GPT-3.5-turboモデル対応
   - シンプルな会話に特化

## 新しいバックエンドの追加方法

1. 新しいバックエンドクラスを作成:

```python
from . import ChatBackend
from typing import Dict, Any, List

class MyNewBackend(ChatBackend):
    def get_name(self) -> str:
        return "My New Backend"
    
    def get_description(self) -> str:
        return "Description of my new backend"
    
    def get_settings_schema(self) -> Dict[str, Any]:
        return {
            "my_setting": "default_value",
            # その他の設定項目
        }
    
    def render_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        settings = settings.copy()
        # Streamlitを使用して設定UIを実装
        settings["my_setting"] = st.text_input("My Setting", settings["my_setting"])
        return settings
    
    def handle_chat(self, messages: List[Dict[str, str]], settings: Dict[str, Any]) -> Dict[str, Any]:
        # チャットロジックを実装
        return {
            "message": {
                "role": "assistant",
                "content": "応答内容"
            },
            "context": {
                # オプションのコンテキスト情報
            }
        }
```

2. バックエンドマネージャーに登録:

```python
# utils/chat_backends/manager.py
from .my_new_backend import MyNewBackend

class ChatBackendManager:
    def _initialize(self):
        # ...
        self.register_backend("my_new_backend", MyNewBackend)
```

## APIインターフェース

### ChatBackend基底クラス

```python
class ChatBackend(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """バックエンドの表示名を返す"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """バックエンドの説明を返す"""
        pass
    
    @abstractmethod
    def get_settings_schema(self) -> Dict[str, Any]:
        """設定のスキーマを返す"""
        pass
    
    @abstractmethod
    def render_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """設定UIをレンダリングし、更新された設定を返す"""
        pass
    
    @abstractmethod
    def handle_chat(self, messages: List[Dict[str, str]], settings: Dict[str, Any]) -> Dict[str, Any]:
        """チャットメッセージを処理し、応答を返す"""
        pass
```

### レスポンスフォーマット

`handle_chat`メソッドは以下の形式のデータを返す必要があります：

```python
{
    "message": {
        "role": "assistant",
        "content": "応答のテキスト"
    },
    "context": {
        # オプションのコンテキスト情報
        "data_points": ["参照情報1", "参照情報2"],  # オプション
        "followup_questions": ["質問1", "質問2"],   # オプション
        # その他のコンテキスト情報
    }
}
```

## 使用例

```python
from utils.chat_backends.manager import ChatBackendManager

# バックエンドマネージャーの取得
manager = ChatBackendManager()

# 利用可能なバックエンドの一覧表示
backends = manager.get_available_backends()

# 特定のバックエンドを選択
manager.set_current_backend("azure_openai")

# 現在のバックエンドを使用
current_backend = manager.get_current_backend()
response = current_backend.handle_chat(messages, settings)