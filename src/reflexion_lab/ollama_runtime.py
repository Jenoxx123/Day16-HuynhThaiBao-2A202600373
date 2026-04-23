from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .schemas import JudgeResult, QAExample, ReflectionEntry


@dataclass
class LLMCall:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


ROLE_DEFAULT_MODELS = {
    "OLLAMA_ACTOR_MODEL": "gemma3:1b",
    "OLLAMA_EVALUATOR_MODEL": "gemma3:4b",
    "OLLAMA_REFLECTOR_MODEL": "gemma3:4b",
}


def _env_model(role_key: str, model_override: str | None = None) -> str:
    if model_override:
        return model_override
    return os.getenv(role_key) or os.getenv("OLLAMA_MODEL") or ROLE_DEFAULT_MODELS.get(role_key, "gemma3:1b")


def _chat(system_prompt: str, user_prompt: str, model: str, expect_json: bool = False) -> LLMCall:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        "stream": False,
    }
    if expect_json:
        payload["format"] = "json"
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url=f"{base_url}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP error {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(
            f"Cannot connect to Ollama at {base_url}. Ensure Ollama is running and accessible."
        ) from exc

    message = result.get("message", {})
    text = message.get("content", "").strip()
    return LLMCall(
        text=text,
        prompt_tokens=int(result.get("prompt_eval_count", 0) or 0),
        completion_tokens=int(result.get("eval_count", 0) or 0),
        latency_ms=int((result.get("total_duration", 0) or 0) / 1_000_000),
    )


def _parse_json(text: str) -> dict:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Expected JSON output from model but got: {text[:300]}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object output from model but got: {type(value).__name__}")
    return value


def actor_answer(example: QAExample, reflection_memory: list[str], model: str | None = None) -> tuple[str, int, int]:
    context_lines = [f"- {chunk.title}: {chunk.text}" for chunk in example.context]
    reflection_block = "\n".join(f"- {item}" for item in reflection_memory) if reflection_memory else "- (none)"
    user_prompt = (
        "Solve the question with only the given context.\n\n"
        f"Question:\n{example.question}\n\n"
        f"Context:\n{chr(10).join(context_lines)}\n\n"
        f"Reflection memory:\n{reflection_block}\n\n"
        "Output only the final answer text."
    )
    call = _chat(ACTOR_SYSTEM, user_prompt, model=_env_model("OLLAMA_ACTOR_MODEL", model))
    return call.text, call.prompt_tokens + call.completion_tokens, call.latency_ms


def evaluator(example: QAExample, answer: str, model: str | None = None) -> tuple[JudgeResult, int, int]:
    user_prompt = (
        "Evaluate prediction quality for a QA item.\n\n"
        f"Question: {example.question}\n"
        f"Gold answer: {example.gold_answer}\n"
        f"Predicted answer: {answer}\n\n"
        "Return JSON only with keys: score (0 or 1), reason (string), "
        "missing_evidence (string array), spurious_claims (string array)."
    )
    call = _chat(EVALUATOR_SYSTEM, user_prompt, model=_env_model("OLLAMA_EVALUATOR_MODEL", model), expect_json=True)
    judge = JudgeResult.model_validate(_parse_json(call.text))
    return judge, call.prompt_tokens + call.completion_tokens, call.latency_ms


def reflector(
    example: QAExample,
    attempt_id: int,
    answer: str,
    judge: JudgeResult,
    model: str | None = None,
) -> tuple[ReflectionEntry, int, int]:
    user_prompt = (
        "Create reflection for the failed attempt.\n\n"
        f"Question: {example.question}\n"
        f"Attempt id: {attempt_id}\n"
        f"Predicted answer: {answer}\n"
        f"Failure reason: {judge.reason}\n"
        f"Missing evidence: {judge.missing_evidence}\n"
        f"Spurious claims: {judge.spurious_claims}\n\n"
        "Return JSON only with keys: attempt_id (int), failure_reason (string), "
        "lesson (string), next_strategy (string)."
    )
    call = _chat(REFLECTOR_SYSTEM, user_prompt, model=_env_model("OLLAMA_REFLECTOR_MODEL", model), expect_json=True)
    reflection = ReflectionEntry.model_validate(_parse_json(call.text))
    return reflection, call.prompt_tokens + call.completion_tokens, call.latency_ms

