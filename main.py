from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Any, Optional
from pipeline import generate_pipeline
import uvicorn

app = FastAPI(
    title="SQLArena AI Question Generator Pipeline",
    description="AI SQL Generator with Prefect + Ollama"
)

class GenerateRequest(BaseModel):
    specs: Optional[List[str]] = ["easy", "medium", "hard"]

class GenerateResponse(BaseModel):
    results: List[Any]

@app.post("/generate", response_model=GenerateResponse)
async def generate_questions(req: GenerateRequest):
    try:
        results = generate_pipeline(req.specs)

        if hasattr(results, 'result'):
            results = [r.result() for r in results]

        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)