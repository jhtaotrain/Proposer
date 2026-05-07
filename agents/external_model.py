from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request


def get_external_prediction(
    *,
    prompt: str,
    provider: str,
    model: str,
    base_url: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    timeout_sec: float = 60.0,
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
) -> dict[str, Any]:
    api_key = os.environ.get(api_key_env)
    if require_api_key and not api_key:
        raise ValueError(f"missing API key in environment variable {api_key_env}")

    payload: dict[str, Any] = {
        "model": model,
        "temperature": 0,
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
    if use_json_response_format:
        payload["response_format"] = {"type": "json_object"}

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
    stripped = text.strip()

    if stripped.startswith("```"):
        stripped = _strip_code_fences(stripped)

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = json.loads(_extract_first_json_object(stripped))

    return _normalize_prediction(parsed)


def _strip_code_fences(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_first_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("could not find a JSON object in model output")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise ValueError("could not extract a complete JSON object from model output")


def _normalize_prediction(parsed: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        raise ValueError("prediction must be a JSON object")

    return {
        "is_ambiguous": bool(parsed.get("is_ambiguous")),
        "compatible_hypotheses": list(parsed.get("compatible_hypotheses") or []),
        "chosen_experiment_id": parsed.get("chosen_experiment_id"),
        "reasoning": str(parsed.get("reasoning", "")),
    }
