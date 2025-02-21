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
    try:
        # Basic validation
        if not request.question:
            raise HTTPException(status_code=400, detail="Question is required")

        if request.approach != "rtr":
            raise HTTPException(status_code=400, detail="Invalid approach value")

        # Normal response
        return {
            "answer": f"This is a mock answer for: {request.question}",
            "thoughts": "Mock thought process explanation",
            "data_points": [
                "Mock reference 1",
                "Mock reference 2",
                "Mock reference 3"
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