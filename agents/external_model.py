from __future__ import annotations

import ast
import json
import os
from typing import Any
from urllib import error, request


PREDICTION_KEYS = {
    "is_ambiguous",
    "compatible_hypotheses",
    "chosen_experiment_id",
    "reasoning",
}


class ModelOutputParseError(ValueError):
    def __init__(self, message: str, *, raw_output: str) -> None:
        super().__init__(message)
        self.raw_output_preview = raw_output[:1000]


def get_external_prediction(
    *,
    prompt: str,
    provider: str,
    model: str,
    base_url: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    timeout_sec: float = 60.0,
    temperature: float = 0.0,
    top_p: float | None = None,
    top_k: int | None = None,
    max_tokens: int | None = None,
    thinking: str = "default",
) -> dict[str, Any]:
    if provider == "openai":
        return _call_openai_chat_completions(
            prompt=prompt,
            model=model,
            base_url=base_url or "https://api.openai.com/v1/chat/completions",
            api_key_env=api_key_env,
            timeout_sec=timeout_sec,
            use_json_response_format=True,
            require_api_key=True,
            allow_vllm_extras=False,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_tokens=max_tokens,
            thinking=thinking,
        )

    if provider == "vllm":
        return _call_openai_chat_completions(
            prompt=prompt,
            model=model,
            base_url=base_url or "http://localhost:8000/v1/chat/completions",
            api_key_env=api_key_env,
            timeout_sec=timeout_sec,
            use_json_response_format=False,
            require_api_key=False,
            allow_vllm_extras=True,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_tokens=max_tokens,
            thinking=thinking,
        )

    raise ValueError(f"unsupported external provider: {provider}")


def _call_openai_chat_completions(
    *,
    prompt: str,
    model: str,
    base_url: str,
    api_key_env: str,
    timeout_sec: float,
    use_json_response_format: bool,
    require_api_key: bool,
    allow_vllm_extras: bool,
    temperature: float,
    top_p: float | None,
    top_k: int | None,
    max_tokens: int | None,
    thinking: str,
) -> dict[str, Any]:
    api_key = os.environ.get(api_key_env)
    if require_api_key and not api_key:
        raise ValueError(f"missing API key in environment variable {api_key_env}")

    payload: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return only a valid JSON object with keys "
                    "is_ambiguous, compatible_hypotheses, chosen_experiment_id, reasoning."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    if top_p is not None:
        payload["top_p"] = top_p
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if use_json_response_format:
        payload["response_format"] = {"type": "json_object"}
    if allow_vllm_extras:
        if top_k is not None:
            payload["top_k"] = top_k
        if thinking != "default":
            payload["chat_template_kwargs"] = {
                "enable_thinking": thinking == "on",
            }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response_json = _post_json(
        url=base_url,
        payload=payload,
        headers=headers,
        timeout_sec=timeout_sec,
    )
    content = response_json["choices"][0]["message"]["content"]
    return _parse_prediction_text(content)


def _post_json(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_sec: float,
) -> dict[str, Any]:
    encoded_payload = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=encoded_payload, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout_sec) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"external model HTTP error {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"failed to contact external model endpoint {url}: {exc}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"external model returned non-JSON response body: {body}") from exc


def _parse_prediction_text(text: str) -> dict[str, Any]:
    stripped = _strip_code_fences(text.strip())
    errors = []

    for candidate in _prediction_object_candidates(stripped):
        try:
            parsed = _parse_object_candidate(candidate)
        except (ValueError, SyntaxError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            continue

        if isinstance(parsed, dict) and PREDICTION_KEYS.intersection(parsed):
            return _normalize_prediction(parsed)

    detail = "; ".join(errors[-3:]) if errors else "no object-like candidate found"
    raise ModelOutputParseError(
        f"could not parse structured prediction from model output: {detail}",
        raw_output=text,
    )


def _strip_code_fences(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _prediction_object_candidates(text: str) -> list[str]:
    candidates = [text]
    candidates.extend(_extract_balanced_object_candidates(text))

    deduped = []
    seen = set()
    for candidate in candidates:
        stripped = _strip_code_fences(candidate.strip())
        if stripped and stripped not in seen:
            deduped.append(stripped)
            seen.add(stripped)
    return deduped


def _parse_object_candidate(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return ast.literal_eval(_pythonize_json_literals(text))


def _extract_balanced_object_candidates(text: str) -> list[str]:
    candidates = []
    depth = 0
    start = None
    quote_char = None
    escape = False

    for index, char in enumerate(text):
        if quote_char is not None:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote_char:
                quote_char = None
            continue

        if char in {"'", '"'}:
            quote_char = char
            continue

        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start : index + 1])
                start = None

    return candidates


def _pythonize_json_literals(text: str) -> str:
    replacements = {
        "true": "True",
        "false": "False",
        "null": "None",
    }
    result = []
    quote_char = None
    escape = False
    index = 0

    while index < len(text):
        char = text[index]
        if quote_char is not None:
            result.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote_char:
                quote_char = None
            index += 1
            continue

        if char in {"'", '"'}:
            quote_char = char
            result.append(char)
            index += 1
            continue

        replaced = False
        for old, new in replacements.items():
            end_index = index + len(old)
            before = text[index - 1] if index > 0 else ""
            after = text[end_index] if end_index < len(text) else ""
            if (
                text[index:end_index] == old
                and not (before.isalnum() or before == "_")
                and not (after.isalnum() or after == "_")
            ):
                result.append(new)
                index = end_index
                replaced = True
                break

        if not replaced:
            result.append(char)
            index += 1

    return "".join(result)


def _normalize_prediction(parsed: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        raise ValueError("prediction must be a JSON object")

    return {
        "is_ambiguous": bool(parsed.get("is_ambiguous")),
        "compatible_hypotheses": list(parsed.get("compatible_hypotheses") or []),
        "chosen_experiment_id": parsed.get("chosen_experiment_id"),
        "reasoning": str(parsed.get("reasoning", "")),
    }
