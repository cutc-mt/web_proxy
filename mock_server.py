from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional, List, Dict, Any

app = FastAPI(title="Mock API Server")

class ChatRequest(BaseModel):
    question: str
    approach: str
    overrides: Dict[str, Any]

@app.post("/ask")
async def chat(request: ChatRequest):
    try:
        # Basic validation
        if not request.question:
            raise HTTPException(status_code=400, detail="Question is required")

        if request.approach != "rtr":
            raise HTTPException(status_code=400, detail="Invalid approach value")

        # Normal response
        return {
            "answer": f"これは質問「{request.question}」に対するモック回答です。",
            "thoughts": "モックの思考プロセスの説明です。",
            "data_points": [
                "参照文献1：日本語のテストデータです。",
                "参照文献2：こちらもテストデータとして日本語を含みます。",
                "参照文献3：最後のテストデータポイントです。"
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        print(f"Failed to start server: {e}")