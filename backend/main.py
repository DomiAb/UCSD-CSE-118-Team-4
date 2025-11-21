from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

"""
Command to run server:
uvicorn main:app --host 0.0.0.0 --port 8000
"""

app = FastAPI()

class ContextRequest(BaseModel):
    transcript: str

class SuggestionResponse(BaseModel):
    options: List[str]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/suggest", response_model=SuggestionResponse)
def suggest(req: ContextRequest):
    t = req.transcript
    # DUMMY behavior for now
    return SuggestionResponse(
        options=[
            f"I heard: '{t}'. Is that right?",
            "Sorry, could you please repeat that?",
            "Give me a moment."
        ]
    )