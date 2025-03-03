from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional, List, Dict, Any, Union
import json
import uuid
from datetime import datetime
import json

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # リクエストの基本情報を出力
        print("\n=== Incoming Request ===")
        print(f"Method: {request.method}")
        print(f"URL: {request.url}")
        
        # ヘッダーを出力
        print("\nHeaders:")
        for name, value in request.headers.items():
            print(f"{name}: {value}")
        
        # ボディを出力（JSONの場合）
        if request.headers.get("content-type") == "application/json":
            body = await request.body()
            if body:
                try:
                    body_json = json.loads(body)
                    print("\nRequest Body:")
                    print(json.dumps(body_json, ensure_ascii=False, indent=2))
                except:
                    print("\nRequest Body: (Invalid JSON)")
                    print(body.decode())
        
        # 元のレスポンスを返す
        response = await call_next(request)
        return response

app = FastAPI(title="Mock API Server")
app.add_middleware(RequestLoggingMiddleware)

# メモリ内データストア
threads: Dict[str, Dict] = {}  # スレッド情報
messages: Dict[str, List[Dict]] = {}  # スレッドごとのメッセージ
thread_orders: List[str] = []  # スレッドの順序（更新日時順）

class ThreadCreate(BaseModel):
    name: str

class ThreadUpdate(BaseModel):
    name: str

class Thread(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str

class ThreadList(BaseModel):
    threads: List[Thread]

class Message(BaseModel):
    content: str
    role: str
    details: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    messages: List[Message]
    context: Optional[Dict[str, Any]] = None
    session_state: Optional[str] = None

class AskRequest(BaseModel):
    question: str
    approach: str
    overrides: Dict[str, Any]

@app.get("/threads", response_model=ThreadList)
async def list_threads():
    """スレッド一覧を取得"""
    thread_list = [threads[thread_id] for thread_id in thread_orders]
    return {"threads": thread_list}

@app.post("/threads", response_model=Thread)
async def create_thread(request: ThreadCreate):
    """新しいスレッドを作成"""
    thread_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    thread = {
        "id": thread_id,
        "name": request.name,
        "created_at": timestamp,
        "updated_at": timestamp
    }
    
    threads[thread_id] = thread
    messages[thread_id] = []
    thread_orders.insert(0, thread_id)
    
    return thread

@app.put("/threads/{thread_id}", response_model=Thread)
async def update_thread(thread_id: str, request: ThreadUpdate):
    """スレッド名を更新"""
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    threads[thread_id]["name"] = request.name
    threads[thread_id]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 更新順を反映
    thread_orders.remove(thread_id)
    thread_orders.insert(0, thread_id)
    
    return threads[thread_id]

@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str):
    """スレッドを削除"""
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    del threads[thread_id]
    del messages[thread_id]
    thread_orders.remove(thread_id)
    
    return {"status": "success"}

@app.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str):
    """スレッドのメッセージ履歴を取得"""
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    return {"messages": messages[thread_id]}

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # 生のリクエストボディを出力
        body = await request.body()
        print("\n=== Raw Request Body ===")
        print(body.decode('utf-8'))
        
        # 送信されたメッセージからユーザーの入力を取得
        last_user_message = request.messages[-1].content if request.messages else None
        if not last_user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        # セッション管理
        session_state = request.session_state or str(uuid.uuid4())

        # レスポンスを作成
        response = {
            "message": {
                "role": "assistant",
                "content": (
                    f"これは「{last_user_message}」に対するモック応答です。\n\n"
                    f"Azure検索デモを参考にした応答を生成します：\n\n"
                    "1. 検索エンジンを使用してドキュメントを検索\n"
                    "2. 関連する情報を抽出して文脈を理解\n"
                    "3. ユーザーの質問に対する具体的な回答を生成\n\n"
                    "以下のドキュメントを参照しました。"
                )
            },
            "context": {
                "data_points": [
                    "Azure OpenAI Service: 大規模言語モデルを活用した自然言語処理",
                    "Azure Cognitive Search: 高度な検索機能とAIによる文書理解",
                    "ハイブリッド検索: ベクトル検索とキーワード検索の組み合わせ"
                ],
                "followup_questions": [
                    "Azure OpenAI Serviceの特徴について詳しく知りたいですか？",
                    "検索機能の具体的な実装方法を見てみましょうか？",
                    "他のAzureサービスとの連携について知りたいですか？"
                ]
            },
            "session_state": session_state
        }
        
        # デバッグ出力
        print("\n=== Chat Response ===")
        print(json.dumps(response, ensure_ascii=False, indent=2))
        
        return response
        
        # レスポンスの内容をデバッグ出力
        response = {
            "message": {
                "role": "assistant",
                "content": f"これは「{last_user_message}」に対するモック応答です。\n\n..."
            },
            "context": {
                "data_points": [
                    "Azure OpenAI Service: 大規模言語モデルを活用した自然言語処理",
                    "Azure Cognitive Search: 高度な検索機能とAIによる文書理解",
                    "ハイブリッド検索: ベクトル検索とキーワード検索の組み合わせ"
                ],
                "followup_questions": [
                    "Azure OpenAI Serviceの特徴について詳しく知りたいですか？",
                    "検索機能の具体的な実装方法を見てみましょうか？",
                    "他のAzureサービスとの連携について知りたいですか？"
                ]
            },
            "session_state": session_state
        }
        print("\n=== Chat Response ===")
        print(json.dumps(response, ensure_ascii=False, indent=2))
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask")
async def ask(request: AskRequest):
    """Simple Q&A用のエンドポイント"""
    try:
        # リクエストの内容をデバッグ出力
        print("\n=== Ask Request ===")
        print("Question:", request.question)
        print("Approach:", request.approach)
        print("Overrides:", request.overrides)
        
        # レスポンスを作成
        response = {
            "answer": (
                f"これは「{request.question}」に対するモック応答です。\n\n"
                f"検索設定：\n"
                f"- アプローチ: {request.approach}\n"
                f"- 検索モード: {request.overrides.get('retrieval_mode', 'hybrid')}\n"
                f"- 上位件数: {request.overrides.get('top', 3)}\n\n"
                "以下のドキュメントを参照しました。"
            ),
            "data_points": [
                "Azure OpenAI Service: 大規模言語モデルを活用した自然言語処理",
                "Azure Cognitive Search: 高度な検索機能とAIによる文書理解",
                "ハイブリッド検索: ベクトル検索とキーワード検索の組み合わせ"
            ],
            "thoughts": (
                "1. 質問を分析して検索クエリを生成\n"
                "2. 関連ドキュメントを検索して情報を抽出\n"
                "3. 抽出した情報を基に回答を生成"
            )
        }
        
        # デバッグ出力
        print("\n=== Ask Response ===")
        print(json.dumps(response, ensure_ascii=False, indent=2))
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("uvicorn")
    logger.setLevel(logging.DEBUG)
    uvicorn.run("mock_server:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")