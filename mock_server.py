from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional, List, Dict, Any

app = FastAPI(title="Mock API Server")

class ChatRequest(BaseModel):
    question: str
    approach: str
    overrides: Dict[str, Any]

@app.post("/chat")
async def chat(request: ChatRequest):
    # エラーをシミュレートする場合（20%の確率）
    if len(request.question) % 5 == 0:
        raise HTTPException(status_code=500, detail="Simulated server error")

    # 通常のレスポンス
    return {
        "answer": f"This is a mock answer for: {request.question}",
        "thoughts": "Mock thought process explanation",
        "data_points": [
            "Mock reference 1",
            "Mock reference 2",
            "Mock reference 3"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        print(f"Failed to start server: {e}")