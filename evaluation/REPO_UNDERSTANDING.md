# Repository Understanding Evaluation

Model: `codellama`; retrieval depth: 5 chunks.

## 1. Which files are involved in user authentication and registration?

**Expected files:** auth.py, models.py

**Retrieved files:** auth.py, models.py, payment.py

**File coverage:** 100.0%

**Answer correctness:** 100.0%

**Hallucination flag:** no

**Guardrail decision:** answered (passed)

**Assessment:** All expected source files were retrieved.

### Response

The files involved in user authentication and registration are:

* auth.py
* models.py

These files contain the functions and classes necessary for user authentication and registration, such as the `login` function, the `find_user` function, the `verify_password` function, the `create_session_token` function, the `User` class, and the `register_user` function.

## 2. What happens after a user submits a registration request end-to-end?

**Expected files:** auth.py, models.py

**Retrieved files:** auth.py, models.py, payment.py

**File coverage:** 100.0%

**Answer correctness:** 0.0%

**Hallucination flag:** no

**Guardrail decision:** refused (INSUFFICIENT_CONTEXT)

**Assessment:** All expected source files were retrieved.

### Response

I do not have sufficient repository evidence to answer that question reliably.

## 3. Which components would be affected if calculate_fee() changes?

**Expected files:** payment.py

**Retrieved files:** auth.py, models.py, payment.py

**File coverage:** 100.0%

**Answer correctness:** 66.7%

**Hallucination flag:** no

**Guardrail decision:** answered (passed)

**Assessment:** All expected source files were retrieved.

### Response

The `calculate_fee()` function is used in the `process_payment()` function, so if the `calculate_fee()` function changes, it would affect the `process_payment()` function.

## 4. Trace user identity from registration through login to a payment.

**Expected files:** auth.py, models.py, payment.py

**Retrieved files:** auth.py, models.py, payment.py

**File coverage:** 100.0%

**Answer correctness:** 0.0%

**Hallucination flag:** no

**Guardrail decision:** refused (UNSUPPORTED_OUTPUT)

**Assessment:** All expected source files were retrieved.

### Response

I could not produce an answer that is sufficiently supported by the retrieved repository context.

## 5. Which database tables are touched across authentication and payment?

**Expected files:** auth.py, payment.py

**Retrieved files:** auth.py, models.py, payment.py

**File coverage:** 100.0%

**Answer correctness:** 100.0%

**Hallucination flag:** no

**Guardrail decision:** answered (passed)

**Assessment:** All expected source files were retrieved.

### Response

The database tables touched across authentication and payment are:

* users (for authentication)
* payments (for payment)

## Overall assessment

| Measure | Result |
|---|---:|
| Questions with every expected file retrieved | 5/5 |
| Mean expected-file coverage | 100.0% |
| Fully correct cross-file answers | 2/5 |
| Mean expected-keyword correctness | 53.3% |
| Answers flagged for hallucination | 0/5 |

The single vector store can answer small cross-file questions when independently similar chunks all fit in top-k, but it has no call graph, symbol relationships, dependency edges, or guaranteed coverage. Semantic top-k retrieval may omit a crucial but lexically dissimilar file and cannot prove end-to-end control flow. A code-intelligence graph/index, such as the Sourcegraph work planned for the following week, is the appropriate next step for reliable repository-wide reasoning.
