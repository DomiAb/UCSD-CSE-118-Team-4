import os
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from LLM_response import (
    DEFAULT_MODEL_ID,
    build_generator,
    build_prompt,
    extract_primary_reply,
)

app = FastAPI(title="SpeechLens Backend")

options: List[str] = []
_llm_pipeline = None


class SuggestRequest(BaseModel):
    data: Optional[str] = None
    heard: Optional[str] = None
    transcript: Optional[str] = None
    context: Optional[str] = ""
    goal: Optional[str] = ""


class SuggestResponse(BaseModel):
    options: List[str]


class SelectInputRequest(BaseModel):
    data: str


class SelectInputResponse(BaseModel):
    selected: str


class LLMRequest(BaseModel):
    heard: Optional[str] = None
    transcript: Optional[str] = None
    context: Optional[str] = "friendly encounter"
    goal: Optional[str] = "be concise and friendly"


class LLMResponse(BaseModel):
    reply: str
    context: str
    goal: str


@app.get("/health")
def health():
    return {"status": "ok"}


def _get_llm_pipeline():
    """Lazily load and cache the text-generation pipeline."""
    global _llm_pipeline
    if _llm_pipeline is not None:
        return _llm_pipeline

    model_id = os.getenv("LLM_MODEL_ID", DEFAULT_MODEL_ID)
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    load_in_4bit = (
        os.getenv("LLM_NO_4BIT", "").lower() not in {"1", "true", "yes"}
    )

    _llm_pipeline = build_generator(
        model_id=model_id,
        hf_token=hf_token,
        load_in_4bit=load_in_4bit,
    )
    return _llm_pipeline


def get_llm_reply(heard_text: str, context: str = "", goal: str = "") -> str:
    """
    Generate a single reply based on the heard text plus extra context and goal.
    """
    prompt = build_prompt(heard_text, context, goal)
    generator = _get_llm_pipeline()
    raw = generator(prompt, num_return_sequences=1)[0]["generated_text"]
    raw_reply = raw.split("Reply:", 1)[-1].strip()
    return extract_primary_reply(raw_reply)


@app.post("/suggest", response_model=SuggestResponse)
async def suggest(req: SuggestRequest):
    heard = req.data or req.heard or req.transcript or ""
    context = req.context or ""
    goal = req.goal or ""

    if not heard:
        raise HTTPException(status_code=400, detail="Missing input text (data/heard/transcript)")

    try:
        reply = await run_in_threadpool(get_llm_reply, heard, context, goal)
    except Exception as exc:  # pragma: no cover - surface LLM issues to client
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {exc}")

    global options
    options = [reply]
    return SuggestResponse(options=options)


@app.post("/select-input", response_model=SelectInputResponse)
async def select_input(req: SelectInputRequest):
    global options

    try:
        number = int(req.data)
        response = options[number - 1]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid option index")

    # HoloLens handles TTS; we just return the text response.
    return SelectInputResponse(selected=response)


@app.post("/llm-suggest", response_model=LLMResponse)
async def llm_suggest(req: LLMRequest):
    heard = req.heard or req.transcript or ""
    context = req.context or "friendly encounter"
    goal = req.goal or "be concise and friendly"

    if not heard:
        raise HTTPException(status_code=400, detail="Missing 'heard' (or 'transcript') in request")

    try:
        reply = await run_in_threadpool(get_llm_reply, heard, context, goal)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {exc}")

    return LLMResponse(reply=reply, context=context, goal=goal)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8765)
