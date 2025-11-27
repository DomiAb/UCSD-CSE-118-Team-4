"""
Quick smoke test for Llama 3.2 3B Instruct (default) or any HF causal LM.

Example:
    python backend/llama31_smoke.py --heard "Can you join us for lunch?" \
        --context "Team meeting" --goal "Be concise and friendly"

Dependencies (install in your env):
    pip install torch transformers accelerate sentencepiece
    # Optional for CUDA quantization: bitsandbytes (>=0.43.1)
    # Optional backend: pip install llama-cpp-python  (for GGUF via llama.cpp)

If the model is gated, set HF_TOKEN/HUGGINGFACE_TOKEN or pass --hf-token.
"""

import argparse
import os
import re
from typing import Optional

DEFAULT_MODEL_ID = os.getenv("LLM_MODEL_ID", "meta-llama/Llama-3.2-3B-Instruct")
DEFAULT_BACKEND = os.getenv("LLM_BACKEND", "torch")  # torch | llama_cpp
DEFAULT_TEMP = 0.4
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_NEW_TOKENS = int(os.getenv("LLM_MAX_NEW_TOKENS", "48"))
DEFAULT_CONTEXT_LEN = int(os.getenv("LLM_CONTEXT_LEN", "512"))


def _token_kwargs(hf_token: Optional[str]) -> dict:
    """Helper so we do not pass auth args when they are not set."""
    return {"token": hf_token} if hf_token else {}


def _build_torch_generator(
    model_id: str,
    hf_token: Optional[str],
    load_in_4bit: bool,
    device_override: Optional[str],
    max_new_tokens: int,
):
    import torch  # Lazy import to allow non-torch backends
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    lower_model = model_id.lower()
    if not hf_token and ("llama-3.1" in lower_model):
        raise RuntimeError(
            "This model is gated on Hugging Face. Please set HF_TOKEN/HUGGINGFACE_TOKEN "
            "or pass --hf-token after accepting the model license."
        )
    token_kwargs = _token_kwargs(hf_token)
    tokenizer = AutoTokenizer.from_pretrained(model_id, **token_kwargs)

    has_cuda = torch.cuda.is_available()
    has_mps = torch.backends.mps.is_available()

    if device_override == "cpu":
        device = "cpu"
    elif device_override == "mps" and has_mps:
        device = "mps"
    else:
        device = "cuda" if has_cuda else "mps" if has_mps else "cpu"

    dtype = torch.float16 if device in ("cuda", "mps") else torch.float32

    model_kwargs = dict(
        torch_dtype=dtype,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        **token_kwargs,
    )
    if device == "cuda":
        # Request 4-bit when CUDA is present; bitsandbytes fails on CPU/MPS.
        if load_in_4bit:
            model_kwargs["load_in_4bit"] = True
        model_kwargs["device_map"] = "auto"
    else:
        model_kwargs["device_map"] = {"": device}

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        **model_kwargs,
    )

    return pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=max_new_tokens,
        temperature=DEFAULT_TEMP,
        top_p=DEFAULT_TOP_P,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )


class _LlamaCppWrapper:
    """Simple wrapper to mimic the HF pipeline interface with llama.cpp."""

    def __init__(self, llm, max_new_tokens: int, temperature: float, top_p: float):
        self.llm = llm
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p

    def __call__(self, prompt, num_return_sequences=1):
        outputs = []
        for _ in range(num_return_sequences):
            res = self.llm(
                prompt,
                max_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                echo=False,
            )
            text = res["choices"][0]["text"]
            outputs.append({"generated_text": prompt + text})
        return outputs


def _build_llama_cpp_generator(
    model_path: str,
    max_new_tokens: int,
    n_ctx: int,
    n_threads: Optional[int],
):
    try:
        from llama_cpp import Llama
    except ImportError as exc:
        raise RuntimeError(
            "llama-cpp-python is not installed. Install it or set LLM_BACKEND=torch."
        ) from exc

    if not model_path or not os.path.exists(model_path):
        raise RuntimeError(
            "LLM_BACKEND=llama_cpp requires LLAMA_CPP_MODEL_PATH to be set to a GGUF file."
        )

    threads = n_threads or int(os.getenv("LLM_THREADS", "4"))
    llm = Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        n_threads=threads,
        n_batch=32,
        logits_all=False,
        verbose=False,
    )
    return _LlamaCppWrapper(llm, max_new_tokens, DEFAULT_TEMP, DEFAULT_TOP_P)


def build_generator(
    model_id: str = DEFAULT_MODEL_ID,
    hf_token: Optional[str] = None,
    load_in_4bit: bool = True,
    device_override: Optional[str] = None,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    backend: str = DEFAULT_BACKEND,
    llama_model_path: Optional[str] = None,
    n_ctx: int = DEFAULT_CONTEXT_LEN,
    n_threads: Optional[int] = None,
):
    """Load the model and create a text-generation pipeline (torch or llama.cpp)."""
    backend = backend.lower()
    if backend == "llama_cpp":
        return _build_llama_cpp_generator(
            model_path=llama_model_path or os.getenv("LLAMA_CPP_MODEL_PATH", ""),
            max_new_tokens=max_new_tokens,
            n_ctx=n_ctx,
            n_threads=n_threads,
        )

    return _build_torch_generator(
        model_id=model_id,
        hf_token=hf_token,
        load_in_4bit=load_in_4bit,
        device_override=device_override,
        max_new_tokens=max_new_tokens,
    )


def build_prompt(heard_text: str, context: str, user_goal: str) -> str:
    return (
        "You assist a user with a speech impairment. Return one clear, natural reply "
        "that fits the goal and context. Do not provide additional explanation. \n"
        f"Context: {context or 'N/A'}\n"
        f"User goal: {user_goal or 'Be concise and polite.'}\n"
        f"Heard text: {heard_text}\n"
        "Reply:"
    )


def extract_primary_reply(text: str) -> str:
    """
    Extract the main reply sentence from a model's raw output.

    Heuristics:
    - Take the first non-empty line.
    - Strip surrounding quotes.
    - Trim to the first sentence boundary if present.
    """
    cleaned = text.strip()
    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    first = lines[0] if lines else cleaned
    first = first.strip(' "“”')

    parts = re.split(r"(?<=[.!?])\s+", first)
    primary = parts[0].strip(' "“”') if parts else first
    return primary or first


def generate_single_reply(
    heard_text: str,
    context: str = "",
    user_goal: str = "",
    model_id: str = DEFAULT_MODEL_ID,
    hf_token: Optional[str] = None,
    load_in_4bit: bool = True,
    device: Optional[str] = None,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    backend: str = DEFAULT_BACKEND,
    llama_model_path: Optional[str] = None,
    n_ctx: int = DEFAULT_CONTEXT_LEN,
    n_threads: Optional[int] = None,
) -> str:
    """Convenience wrapper if you just need one reply in code."""
    prompt = build_prompt(heard_text, context, user_goal)
    generator = build_generator(
        model_id=model_id,
        hf_token=hf_token,
        load_in_4bit=load_in_4bit,
        device_override=device,
        max_new_tokens=max_new_tokens,
        backend=backend,
        llama_model_path=llama_model_path,
        n_ctx=n_ctx,
        n_threads=n_threads,
    )
    raw = generator(prompt, num_return_sequences=1)[0]["generated_text"]
    raw_reply = raw.split("Reply:", 1)[-1].strip()
    return extract_primary_reply(raw_reply)


def main():
    parser = argparse.ArgumentParser(
        description="Run a local smoke test against Llama 3.2 3B Instruct."
    )
    parser.add_argument("--heard", required=True, help="What the other person said.")
    parser.add_argument(
        "--context",
        default="",
        help="Optional short context for the interaction (e.g., 'in class').",
    )
    parser.add_argument(
        "--goal",
        default="Be concise and polite.",
        help="Desired tone or goal for the reply.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_ID,
        help="Hugging Face model id to load (torch backend).",
    )
    parser.add_argument(
        "--hf-token",
        default=None,
        help="Hugging Face token if the model is gated (falls back to HF_TOKEN env).",
    )
    parser.add_argument(
        "--no-4bit",
        action="store_true",
        help="Disable 4-bit loading (use this if bitsandbytes is unavailable).",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "mps"],
        default="auto",
        help="Force device selection (default auto). On Jetson Nano, try cpu.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=DEFAULT_MAX_NEW_TOKENS,
        help=f"Limit new tokens (default {DEFAULT_MAX_NEW_TOKENS}). Lower to reduce memory.",
    )
    parser.add_argument(
        "--backend",
        choices=["torch", "llama_cpp"],
        default=DEFAULT_BACKEND,
        help="Inference backend. Use llama_cpp with a GGUF on low-memory devices.",
    )
    parser.add_argument(
        "--llama-model-path",
        default=os.getenv("LLAMA_CPP_MODEL_PATH", ""),
        help="Path to GGUF model for llama_cpp backend.",
    )
    parser.add_argument(
        "--n-ctx",
        type=int,
        default=DEFAULT_CONTEXT_LEN,
        help=f"Context length (default {DEFAULT_CONTEXT_LEN}). Lower to save memory.",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=None,
        help="Threads for llama_cpp backend.",
    )
    args = parser.parse_args()

    hf_token = args.hf_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")

    generator = build_generator(
        model_id=args.model,
        hf_token=hf_token,
        load_in_4bit=not args.no_4bit,
        device_override=None if args.device == "auto" else args.device,
        max_new_tokens=args.max_new_tokens,
        backend=args.backend,
        llama_model_path=args.llama_model_path,
        n_ctx=args.n_ctx,
        n_threads=args.threads,
    )
    prompt = build_prompt(args.heard, args.context, args.goal)
    result = generator(prompt, num_return_sequences=1)[0]["generated_text"]
    reply = result.split("Reply:", 1)[-1].strip()

    print("LLM reply:")
    print(reply)


if __name__ == "__main__":
    main()
