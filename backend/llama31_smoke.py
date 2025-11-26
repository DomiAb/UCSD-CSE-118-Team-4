"""
Quick smoke test for Llama 3.1 8B Instruct on a local GPU (Jetson).

Example:
    python backend/llama31_smoke.py --heard "Can you join us for lunch?" \
        --context "Team meeting" --goal "Be concise and friendly"

Dependencies (install in your env):
    pip install torch transformers accelerate bitsandbytes sentencepiece

If the model is gated, set HF_TOKEN/HUGGINGFACE_TOKEN or pass --hf-token.
"""

import argparse
import os
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

DEFAULT_MODEL_ID = "meta-llama/Meta-Llama-3.1-8B-Instruct"
DEFAULT_TEMP = 0.4
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_NEW_TOKENS = 96


def _token_kwargs(hf_token: Optional[str]) -> dict:
    """Helper so we do not pass auth args when they are not set."""
    return {"token": hf_token} if hf_token else {}


def build_generator(
    model_id: str = DEFAULT_MODEL_ID, hf_token: Optional[str] = None
):
    """Load the model and create a text-generation pipeline."""
    if "meta-llama" in model_id.lower() and not hf_token:
        raise RuntimeError(
            "This model is gated on Hugging Face. Please set HF_TOKEN/HUGGINGFACE_TOKEN "
            "or pass --hf-token after accepting the model license."
        )
    token_kwargs = _token_kwargs(hf_token)
    tokenizer = AutoTokenizer.from_pretrained(model_id, **token_kwargs)

    has_cuda = torch.cuda.is_available()
    has_mps = torch.backends.mps.is_available()
    device = "cuda" if has_cuda else "mps" if has_mps else "cpu"
    dtype = torch.float16 if device in ("cuda", "mps") else torch.float32

    model_kwargs = dict(
        torch_dtype=dtype,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        **token_kwargs,
    )
    if device == "cuda":
        # Only request 4-bit when CUDA is present; bitsandbytes fails on CPU/MPS.
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
        max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
        temperature=DEFAULT_TEMP,
        top_p=DEFAULT_TOP_P,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )


def build_prompt(heard_text: str, context: str, user_goal: str) -> str:
    return (
        "You assist a user with a speech impairment. Return one clear, natural reply "
        "that fits the goal and context.\n"
        f"Context: {context or 'N/A'}\n"
        f"User goal: {user_goal or 'Be concise and polite.'}\n"
        f"Heard text: {heard_text}\n"
        "Reply:"
    )


def generate_single_reply(
    heard_text: str,
    context: str = "",
    user_goal: str = "",
    model_id: str = DEFAULT_MODEL_ID,
    hf_token: Optional[str] = None,
) -> str:
    """Convenience wrapper if you just need one reply in code."""
    prompt = build_prompt(heard_text, context, user_goal)
    generator = build_generator(model_id=model_id, hf_token=hf_token)
    raw = generator(prompt, num_return_sequences=1)[0]["generated_text"]
    return raw.split("Reply:", 1)[-1].strip()


def main():
    parser = argparse.ArgumentParser(
        description="Run a local smoke test against Llama 3.1 8B Instruct."
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
        help="Hugging Face model id to load (default: Llama 3.1 8B Instruct).",
    )
    parser.add_argument(
        "--hf-token",
        default=None,
        help="Hugging Face token if the model is gated (falls back to HF_TOKEN env).",
    )
    args = parser.parse_args()

    hf_token = args.hf_token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")

    generator = build_generator(model_id=args.model, hf_token=hf_token)
    prompt = build_prompt(args.heard, args.context, args.goal)
    result = generator(prompt, num_return_sequences=1)[0]["generated_text"]
    reply = result.split("Reply:", 1)[-1].strip()

    print("LLM reply:")
    print(reply)


if __name__ == "__main__":
    main()
