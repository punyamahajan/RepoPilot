"""Systematically test candidate LLM outputs before application acceptance."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.guardrails import validate_output


CONTEXT = """auth.py (chunk 0):
def login(username, password):
    user = find_user(username)
    if user and verify_password(password, user.password_hash):
        return create_session_token(user)
payment.py (chunk 0):
def calculate_fee(amount, rate=0.03):
    return round(amount * rate, 2)
"""

CASES = [
    {
        "id": "relevant-grounded",
        "condition": "Relevant and supported answer is accepted",
        "prompt": "How is the payment fee calculated?",
        "answer": "calculate_fee multiplies the amount by the default 0.03 rate and rounds the result to two decimals.",
        "expected": True,
    },
    {
        "id": "unsupported-function",
        "condition": "Unsupported code claim is rejected",
        "prompt": "How does login work?",
        "answer": "login calls send_login_email() before creating a token.",
        "expected": False,
    },
    {
        "id": "unsupported-file",
        "condition": "Invented source file is rejected",
        "prompt": "Where is login implemented?",
        "answer": "Login is implemented in sessions.py.",
        "expected": False,
    },
    {
        "id": "irrelevant-output",
        "condition": "Irrelevant output is rejected",
        "prompt": "How does login work?",
        "answer": "Bananas are yellow tropical fruit.",
        "expected": False,
    },
    {
        "id": "empty-output",
        "condition": "Empty output is rejected",
        "prompt": "How does login work?",
        "answer": "",
        "expected": False,
    },
    {
        "id": "generated-code",
        "condition": "Clearly requested generated code can introduce test symbols",
        "prompt": "Write a unit test for calculate_fee.",
        "answer": "```python\ndef test_calculate_fee():\n    assert calculate_fee(100) == 3.0\n```",
        "expected": True,
    },
    {
        "id": "model-insufficient",
        "condition": "A model insufficiency signal becomes a controlled refusal",
        "prompt": "How is logout implemented?",
        "answer": "I do not have sufficient repository evidence to answer that question reliably.",
        "expected": False,
        "reason": "INSUFFICIENT_CONTEXT",
    },
    {
        "id": "unsupported-relationship",
        "condition": "Unsupported function-call relationship is rejected",
        "prompt": "Which functions depend on calculate_fee?",
        "answer": "calculate_fee() is used by log_transaction().",
        "expected": False,
    },
    {
        "id": "invalid-format",
        "condition": "Unbalanced generated-code fence is rejected",
        "prompt": "Write a unit test for calculate_fee.",
        "answer": "```python\ndef test_fee():\n    assert calculate_fee(100) == 3.0",
        "expected": False,
    },
    {
        "id": "unsupported-flow",
        "condition": "Unsupported cross-component workflow is rejected",
        "prompt": "Trace identity from login to payment.",
        "answer": "The session token is stored in browser storage and included in a request header for payment.",
        "expected": False,
    },
]


def evaluate_cases():
    rows = []
    for case in CASES:
        decision = validate_output(case["prompt"], case["answer"], CONTEXT)
        passed = decision.allowed == case["expected"]
        if case.get("reason"):
            passed = passed and decision.reason_code == case["reason"]
        rows.append({**case, "actual": decision.allowed, "reason": decision.reason_code, "passed": passed})
    return rows


def render_report(rows):
    passed = sum(row["passed"] for row in rows)
    lines = [
        "# AI Output Test Report",
        "",
        "LLM output is treated as an untrusted candidate. It is accepted only when it is non-empty, within the response limit, relevant to the question/evidence, and contains no unsupported factual file or function claims. Explicit model uncertainty is converted into the standard controlled refusal.",
        "",
        "## Pass/fail criteria",
        "",
        "- Supported, relevant factual answers must be accepted.",
        "- Empty, irrelevant, or unsupported factual answers must be rejected.",
        "- Requested generated/refactored code may introduce new test/helper symbols, because it is a proposal rather than a claim about existing code.",
        "- An insufficiency statement must be rejected as an answer and returned as a controlled `INSUFFICIENT_CONTEXT` refusal.",
        "",
        "## Results",
        "",
        "| Test | Condition | Expected | Actual | Reason | Result |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['condition']} | {'accept' if row['expected'] else 'reject'} | "
            f"{'accept' if row['actual'] else 'reject'} | {row['reason'] or 'none'} | {'PASS' if row['passed'] else 'FAIL'} |"
        )
    lines += [
        "",
        "## Summary",
        "",
        f"**{passed}/{len(rows)} tests passed ({passed / len(rows):.1%}).** The tests are deterministic and run without an LLM, so regressions in the acceptance policy can be detected quickly before live model evaluation.",
        "",
    ]
    return "\n".join(lines)


def main():
    rows = evaluate_cases()
    json_path = os.path.join(os.path.dirname(__file__), "AI_OUTPUT_TEST_RESULTS.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump({"results": rows}, handle, indent=2)
    path = os.path.join(os.path.dirname(__file__), "AI_OUTPUT_TEST_REPORT.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_report(rows))
    print(f"Wrote {path} and {json_path}; {sum(row['passed'] for row in rows)}/{len(rows)} passed")
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
