"""Transparent, dependency-light metrics used by the Week 4 evaluation."""

import ast
import math
import re


def correctness(response: str, expected_answer) -> float:
    """Return matched expected keywords divided by all expected keywords (case-insensitive substrings)."""
    keywords = expected_answer if isinstance(expected_answer, list) else [expected_answer]
    keywords = [str(k).lower() for k in keywords if str(k).strip()]
    return sum(k in response.lower() for k in keywords) / len(keywords) if keywords else 0.0


def cosine_similarity(a: list, b: list) -> float:
    """Return dot(a,b)/(L2(a)*L2(b)); return zero when dimensions/norms are invalid."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    denominator = math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b))
    return dot / denominator if denominator else 0.0


def relevance(response_embedding: list, question_embedding: list) -> float:
    """Return cosine similarity between Ollama embeddings of the response and question."""
    return cosine_similarity(response_embedding, question_embedding)


def retrieval_quality(retrieved_chunks: list, expected_file: str) -> float:
    """Return 1 when the first retrieved chunk source equals/ends with expected_file, otherwise 0."""
    if not retrieved_chunks or not expected_file:
        return 0.0
    source = retrieved_chunks[0].split(" (chunk", 1)[0].replace("\\", "/")
    return float(source == expected_file or source.endswith("/" + expected_file))


def hallucination_flag(response: str, context: str) -> bool:
    """Flag function-call or code-file names in the answer that do not occur in retrieved context."""
    identifiers = set(re.findall(r"\b[A-Za-z_]\w*\s*\(", response))
    identifiers = {x.strip()[:-1].strip() for x in identifiers}
    files = set(re.findall(r"\b[\w.-]+\.(?:py|js|ts|md|json|ya?ml)\b", response))
    claims = {x for x in identifiers if x not in {"if", "for", "while", "print", "return"}} | files
    return any(claim not in context for claim in claims)


def test_pass_rate(response: str, test_case: dict | None):
    """Execute fenced Python defining the named function and return whether expression equals expected; None means skip."""
    if not test_case:
        return None
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
    source = "\n".join(blocks) if blocks else response
    try:
        tree = ast.parse(source)
        allowed = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.Import, ast.ImportFrom))]
        namespace = {"__builtins__": {"len": len, "round": round, "sum": sum, "min": min, "max": max, "range": range, "type": type}}
        exec(compile(ast.Module(body=allowed, type_ignores=[]), "<model-response>", "exec"), namespace)
        return bool(eval(test_case["expression"], namespace) == test_case["expected"])
    except Exception:
        return False


def response_latency(start_seconds: float, end_seconds: float) -> float:
    """Return end monotonic wall-clock timestamp minus start timestamp in seconds."""
    return max(0.0, end_seconds - start_seconds)


def token_usage(prompt_eval_count: int, eval_count: int) -> dict:
    """Return Ollama prompt, completion, and summed token counts from /api/generate."""
    return {"prompt_tokens": prompt_eval_count, "completion_tokens": eval_count,
            "total_tokens": prompt_eval_count + eval_count}


def resource_usage(samples: list) -> dict:
    """Return arithmetic mean CPU percent and RSS MiB across psutil samples during a request."""
    if not samples:
        return {"cpu_percent_avg": 0.0, "memory_mb_avg": 0.0}
    return {"cpu_percent_avg": sum(x[0] for x in samples)/len(samples),
            "memory_mb_avg": sum(x[1] for x in samples)/len(samples)}
