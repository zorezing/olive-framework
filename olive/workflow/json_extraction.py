import json
import re
from typing import Any


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCED_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(raw: str) -> Any:
    """Best-effort extraction of a JSON value from a chat model response.

    Reasoning models routinely wrap their answer in <think> blocks,
    markdown code fences, or trailing commentary instead of returning
    bare JSON, even when the request explicitly asks for JSON-only
    output (observed live with deepseek-r1:8b through Ollama).
    """

    candidates = [raw]

    without_think = _THINK_BLOCK.sub("", raw).strip()
    if without_think and without_think != raw:
        candidates.append(without_think)

    fenced = _FENCED_BLOCK.search(without_think or raw)
    if fenced:
        candidates.append(fenced.group(1).strip())

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Last resort: parse the first balanced JSON value found, ignoring
    # any trailing commentary the model kept generating afterward.
    for candidate in candidates:
        start = candidate.find("{")
        if start == -1:
            continue
        try:
            value, _ = json.JSONDecoder().raw_decode(candidate[start:])
            return value
        except json.JSONDecodeError:
            continue

    raise ValueError("Model output is not valid JSON")
