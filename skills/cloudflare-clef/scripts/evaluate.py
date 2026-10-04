#!/usr/bin/env python3
"""Standard-library client for the deployed Clef /v1/systemone text API."""

import argparse
import json
import math
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPException


DEFAULT_ENDPOINT = "http://127.0.0.1:8000/v1/systemone"
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Keep context and bearer credentials on the configured endpoint.
        return None


ALLOWED_MODELS = {"clef", "clef-flash", "Cloudflare/clef", "@cf/cloudflare/clef", "@cf/cloudflare/clef-flash"}


def _identifier(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _append_log(entry):
    """One append-only write per metadata record; logging never changes the verdict."""
    if os.getenv("CLEF_LOG_ENABLED", "1") == "0":
        return
    try:
        path = Path(os.getenv("CLEF_LOG_PATH", str(Path.home() / ".local/state/clef/events.jsonl"))).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        data = json.dumps({"schema_version": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            **entry}, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
        descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.chmod(path, 0o600)
            os.write(descriptor, data)
        finally:
            os.close(descriptor)
    except (OSError, ValueError, TypeError):
        pass


def _outcome(result):
    if result is None:
        return {"outcome": "error", "error_code": "CLEF_CLIENT_EXCEPTION"}
    if "error" in result:
        return {"outcome": "error", "error_code": result["error"],
            **({"http_status": result["http_status"]} if "http_status" in result else {})}
    return {"outcome": "success"}


def evaluate_clef(state, question_type: str, instructions: str, choices=None, *, levels=None) -> dict:
    """Return a typed verdict; log metadata for Python, CLI and subprocess callers alike."""
    started = time.perf_counter()
    source = os.getenv("CLEF_LOG_SOURCE", "cloudflare-clef")
    if not source or len(source) > 48 or not all(c in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in source):
        source = "cloudflare-clef"
    model = os.getenv("CLEF_MODEL", "clef")
    context = {"call_id": _identifier(os.getenv("CLEF_CALL_ID")) or str(uuid.uuid4()),
        "source": source, "primitive": question_type if question_type in ("noul", "choice", "score") else "unknown",
        "attempt_count": 0}
    if model in ALLOWED_MODELS:
        context["model"] = model
    run_id = _identifier(os.getenv("CLEF_RUN_ID"))
    if run_id:
        context["run_id"] = run_id
    result = None
    try:
        result = _evaluate_clef(state, question_type, instructions, choices, levels=levels, context=context)
        return result
    finally:
        numeric = {key: result[key] for key in ("noul", "score", "confidence")
            if result is not None and key in result and _number(result[key], 0, 15)}
        _append_log({**context, "event": "call", **_outcome(result), **numeric,
            "retry_count": max(0, context["attempt_count"] - 1),
            "fallback_used": bool(result and result.get("fallback_used")),
            "duration_ms": round((time.perf_counter() - started) * 1000, 3)})


def _error(code, message, status=None):
    result = {"error": code, "message": message, "fallback_used": True}
    if status is not None:
        result["http_status"] = status
    return result


def _number(value, minimum=0.0, maximum=1.0):
    return (
        type(value) in (int, float)
        and minimum <= value <= maximum
        and math.isfinite(value)
    )


def _validate_answer(answer, question):
    kind = question["type"]
    fields = {
        "noul": {"type", "noul"},
        "choice": {"type", "choice", "confidence", "probabilities"},
        "score": {"type", "score", "confidence", "legend", "probabilities"},
    }
    if not isinstance(answer, dict) or answer.get("type") != kind or set(answer) != fields[kind]:
        raise ValueError("Missing or mismatched verdict type")
    if kind == "noul":
        if not _number(answer.get("noul")):
            raise ValueError("noul must be a finite probability in [0, 1]")
        return answer

    criteria = question["criteria"]
    keys = set(criteria) if kind == "choice" else {str(i) for i in range(len(criteria))}
    probabilities = answer.get("probabilities")
    if (
        not isinstance(probabilities, dict)
        or set(probabilities) != keys
        or not all(_number(p) for p in probabilities.values())
        # Clef rounds each probability to four decimals (up to 64 options).
        or abs(sum(probabilities.values()) - 1.0) > len(keys) * 0.00005 + 1e-8
        or not _number(answer.get("confidence"))
    ):
        raise ValueError("Invalid probabilities or confidence")
    if abs(answer["confidence"] - max(probabilities.values())) > 0.0001:
        raise ValueError("Clef confidence does not match the largest option probability")
    if kind == "choice":
        selected = answer.get("choice")
        if not isinstance(selected, str) or selected not in keys:
            raise ValueError("choice is outside the requested criteria")
        if probabilities[selected] != max(probabilities.values()):
            raise ValueError("choice is not a highest-probability option")
    else:
        if not _number(answer.get("score"), 0.0, len(criteria) - 1):
            raise ValueError("score is outside the requested level range")
        legend = {str(i): level for i, level in enumerate(criteria)}
        if answer.get("legend") != legend:
            raise ValueError("score legend does not match the requested levels")
        expected = sum(int(key) * p for key, p in probabilities.items())
        tolerance = 0.00005 * (1 + sum(range(len(criteria)))) + 1e-8
        if abs(answer["score"] - expected) > tolerance:
            raise ValueError("score does not match the probability-weighted level index")
    return answer


def _evaluate_clef(state, question_type: str, instructions: str, choices=None, *, levels=None, context) -> dict:
    """Return a validated verdict or an error dict; never invent a fallback verdict.

    choices: list of labels or dict mapping labels to descriptions.
    levels: ordered list of score descriptions, indexed from zero.
    Configuration is read from CLEF_* environment variables on each call.
    """
    try:
        if question_type not in ("noul", "choice", "score"):
            raise ValueError("type must be noul, choice, or score")
        if not isinstance(instructions, str) or not instructions.strip():
            raise ValueError("instructions must be a non-empty string")
        question = {"type": question_type, "instructions": instructions}
        if question_type == "choice":
            if isinstance(choices, list):
                if not all(isinstance(label, str) and label.strip() for label in choices):
                    raise ValueError("choices must contain non-empty strings")
                if len(set(choices)) != len(choices):
                    raise ValueError("choices must be unique")
                choices = dict(zip(choices, choices))
            if (
                not isinstance(choices, dict) or not 1 <= len(choices) <= 64
                or not all(isinstance(k, str) and k.strip() for k in choices)
            ):
                raise ValueError("choice requires 1-64 named choices")
            question["criteria"] = choices
        elif choices is not None:
            raise ValueError("choices is only valid for choice")
        if question_type == "score":
            if not isinstance(levels, list) or not 1 <= len(levels) <= 16:
                raise ValueError("score requires 1-16 ordered levels")
            question["criteria"] = levels
        elif levels is not None:
            raise ValueError("levels is only valid for score")
        payload = json.dumps({
            "model": os.getenv("CLEF_MODEL", "clef"),
            "state": state,
            "questions": {"verdict": question},
        }, ensure_ascii=False, allow_nan=False).encode("utf-8")
        context["request_bytes"] = len(payload)
        if "criteria" in question:
            context["candidate_count"] = len(question["criteria"])
    except (ValueError, TypeError) as exc:
        return _error("CLEF_INVALID_INPUT", str(exc))

    try:
        endpoint = os.getenv("CLEF_BACKEND_URL", DEFAULT_ENDPOINT)
        parsed = urllib.parse.urlsplit(endpoint)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None:
            raise ValueError("CLEF_BACKEND_URL must be an HTTP(S) URL without embedded credentials")
        if os.getenv("CLEF_MODEL", "clef") not in ALLOWED_MODELS:
            raise ValueError(f"CLEF_MODEL must be one of: {', '.join(sorted(ALLOWED_MODELS))}")
        timeout = float(os.getenv("CLEF_TIMEOUT", "10.0"))
        retries = int(os.getenv("CLEF_MAX_RETRIES", "2"))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("CLEF_TIMEOUT must be finite and positive")
        if not 0 <= retries <= 5:
            raise ValueError("CLEF_MAX_RETRIES must be an integer from 0 to 5")
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("CLEF_API_KEY", "")
        if api_key:
            if "\r" in api_key or "\n" in api_key:
                raise ValueError("CLEF_API_KEY must not contain newlines")
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        opener = urllib.request.build_opener(_NoRedirect())
    except (ValueError, TypeError) as exc:
        return _error("CLEF_INVALID_CONFIG", str(exc))

    for attempt in range(retries + 1):
        attempt_started = time.perf_counter()
        context["attempt_count"] += 1
        context.pop("http_status", None)
        status = None
        result = None
        try:
            with opener.open(req, timeout=timeout) as response:
                status = response.status
                context["http_status"] = status
                if response.status != 200:
                    result = _error("CLEF_HTTP_ERROR", "Expected HTTP 200", response.status)
                    return result
                data = json.loads(response.read().decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object from Clef")
            if data.get("success") is False and "errors" in data:
                result = _error("CLEF_HTTP_ERROR", f"Cloudflare API error: {json.dumps(data['errors'], ensure_ascii=False)}")
                return result
            # 严格兼容 Cloudflare Client v4 API 标准响应信封 {"result": {...}, "success": true}
            if data.get("success") is True and isinstance(data.get("result"), dict) and "answers" in data["result"]:
                payload_data = data["result"]
            else:
                payload_data = data
            if not isinstance(payload_data, dict) or "error" in payload_data or not isinstance(payload_data.get("answers"), dict):
                raise ValueError("Expected answers.verdict in the SystemOne response")
            usage = payload_data.get("usage", {})
            if isinstance(usage, dict):
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    if type(usage.get(key)) is int and usage[key] >= 0:
                        context[key] = usage[key]
            if isinstance(payload_data.get("model"), str) and payload_data["model"] in ALLOWED_MODELS:
                context["served_model"] = payload_data["model"]
            result = _validate_answer(payload_data["answers"].get("verdict"), question)
            return result
        except urllib.error.HTTPError as exc:
            status = exc.code
            context["http_status"] = status
            exc.close()
            if status not in RETRYABLE_STATUSES:
                result = _error("CLEF_HTTP_ERROR", "Clef rejected the request", status)
                return result
            result = _error("CLEF_SERVICE_UNAVAILABLE", "Clef remained unavailable after retries", status)
        except (urllib.error.URLError, OSError, HTTPException):
            result = _error("CLEF_SERVICE_UNAVAILABLE", "Connection failed or timed out after retries")
        except (ValueError, UnicodeError) as exc:
            result = _error("CLEF_INVALID_RESPONSE", str(exc))
            return result
        finally:
            _append_log({**context, "event": "attempt", "attempt": attempt + 1,
                "transport": "http", **_outcome(result),
                **({"http_status": status} if status is not None else {}),
                "duration_ms": round((time.perf_counter() - attempt_started) * 1000, 3)})
        if attempt < retries:
            time.sleep(0.5 * 2 ** attempt)
    return result


def main():
    parser = argparse.ArgumentParser(description="Evaluate one typed question via local Cloudflare Clef")
    parser.add_argument("--state", required=True, help="Context, diff, or intent text")
    parser.add_argument("--type", choices=["noul", "choice", "score"], required=True)
    parser.add_argument("--instructions", required=True, help="Narrow question to evaluate")
    parser.add_argument("--choices", nargs="+", help="Named options for choice")
    parser.add_argument("--levels", nargs="+", help="Ordered descriptions for score (zero-based)")
    args = parser.parse_args()
    result = evaluate_clef(args.state, args.type, args.instructions, args.choices, levels=args.levels)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
