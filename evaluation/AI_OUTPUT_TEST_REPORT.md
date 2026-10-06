# AI Output Test Report

LLM output is treated as an untrusted candidate. It is accepted only when it is non-empty, within the response limit, relevant to the question/evidence, and contains no unsupported factual file or function claims. Explicit model uncertainty is converted into the standard controlled refusal.

## Pass/fail criteria

- Supported, relevant factual answers must be accepted.
- Empty, irrelevant, or unsupported factual answers must be rejected.
- Requested generated/refactored code may introduce new test/helper symbols, because it is a proposal rather than a claim about existing code.
- An insufficiency statement must be rejected as an answer and returned as a controlled `INSUFFICIENT_CONTEXT` refusal.

## Results

| Test | Condition | Expected | Actual | Reason | Result |
|---|---|---|---|---|---|
| relevant-grounded | Relevant and supported answer is accepted | accept | accept | none | PASS |
| unsupported-function | Unsupported code claim is rejected | reject | reject | UNSUPPORTED_OUTPUT | PASS |
| unsupported-file | Invented source file is rejected | reject | reject | UNSUPPORTED_OUTPUT | PASS |
| irrelevant-output | Irrelevant output is rejected | reject | reject | UNSUPPORTED_OUTPUT | PASS |
| empty-output | Empty output is rejected | reject | reject | UNSUPPORTED_OUTPUT | PASS |
| generated-code | Clearly requested generated code can introduce test symbols | accept | accept | none | PASS |
| model-insufficient | A model insufficiency signal becomes a controlled refusal | reject | reject | INSUFFICIENT_CONTEXT | PASS |
| unsupported-relationship | Unsupported function-call relationship is rejected | reject | reject | UNSUPPORTED_OUTPUT | PASS |
| invalid-format | Unbalanced generated-code fence is rejected | reject | reject | UNSUPPORTED_OUTPUT | PASS |
| unsupported-flow | Unsupported cross-component workflow is rejected | reject | reject | UNSUPPORTED_OUTPUT | PASS |

## Summary

**10/10 tests passed (100.0%).** The tests are deterministic and run without an LLM, so regressions in the acceptance policy can be detected quickly before live model evaluation.
