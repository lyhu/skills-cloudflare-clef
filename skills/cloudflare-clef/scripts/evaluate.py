#!/usr/bin/env python3
"""Standard-library client for the deployed Clef /v1/systemone text API."""

import argparse
import json
import math
import os
import time
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


def evaluate_clef(state, question_type: str, instructions: str, choices=None, *, levels=None) -> dict:
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
    except (ValueError, TypeError) as exc:
        return _error("CLEF_INVALID_INPUT", str(exc))

    try:
        endpoint = os.getenv("CLEF_BACKEND_URL", DEFAULT_ENDPOINT)
        parsed = urllib.parse.urlsplit(endpoint)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None:
            raise ValueError("CLEF_BACKEND_URL must be an HTTP(S) URL without embedded credentials")
        if os.getenv("CLEF_MODEL", "clef") not in ("clef", "Cloudflare/clef"):
            raise ValueError("CLEF_MODEL must be clef or Cloudflare/clef")
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
        try:
            with opener.open(req, timeout=timeout) as response:
                if response.status != 200:
                    return _error("CLEF_HTTP_ERROR", "Expected HTTP 200", response.status)
                data = json.loads(response.read().decode("utf-8"))
            if not isinstance(data, dict) or "error" in data or not isinstance(data.get("answers"), dict):
                raise ValueError("Expected answers.verdict in the SystemOne response")
            return _validate_answer(data["answers"].get("verdict"), question)
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            if status not in RETRYABLE_STATUSES:
                return _error("CLEF_HTTP_ERROR", "Clef rejected the request", status)
            result = _error("CLEF_SERVICE_UNAVAILABLE", "Clef remained unavailable after retries", status)
        except (urllib.error.URLError, OSError, HTTPException):
            result = _error("CLEF_SERVICE_UNAVAILABLE", "Connection failed or timed out after retries")
        except (ValueError, UnicodeError) as exc:
            return _error("CLEF_INVALID_RESPONSE", str(exc))
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
