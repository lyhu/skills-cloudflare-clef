"""Python integration template (Python 3.9+, standard library only).

Copy this file and ../scripts/evaluate.py into the same application directory.
Configure CLEF_* environment variables; import evaluate_clef from this module.
The shared client returns a typed answer dict or a fail-closed error dict.
"""

from evaluate import evaluate_clef


def assess_command(command: str, cwd: str, intended_scope: str) -> dict:
    """Return risk probability; the host owns policy and execution permission."""
    return evaluate_clef(
        state={"command": command, "cwd": cwd, "intended_scope": intended_scope},
        question_type="noul",
        instructions="Could this command destroy valuable data outside intended_scope?",
    )


def route_issue(issue: str) -> dict:
    return evaluate_clef(
        state=issue,
        question_type="choice",
        instructions="Which handler should investigate this issue?",
        choices={
            "technical": "Software defects or service outages",
            "billing": "Payments, invoices, or refunds",
            "review": "Insufficient evidence or no matching handler",
        },
    )


def score_review(diff_and_evidence: str) -> dict:
    return evaluate_clef(
        state=diff_and_evidence,
        question_type="score",
        instructions="How complete is the test coverage for the specified behavior?",
        levels=[
            "No relevant tests",
            "Some specified behaviors tested",
            "All specified behaviors and failure cases tested",
        ],
    )


if __name__ == "__main__":
    import json

    result = route_issue("Checkout requests fail with HTTP 500.")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if "error" in result else 0)
