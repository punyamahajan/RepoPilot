"""Deterministic input, retrieval, and output guardrails for RepoPilot."""

import ast
import os
import re
from dataclasses import dataclass, field


MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "2000"))
MAX_RETRIEVAL_K = int(os.getenv("MAX_RETRIEVAL_K", "5"))
MIN_RETRIEVAL_SCORE = float(os.getenv("MIN_RETRIEVAL_SCORE", "0.20"))
MAX_RESPONSE_CHARS = int(os.getenv("MAX_RESPONSE_CHARS", "8000"))

REFUSALS = {
    "INVALID_INPUT": "I cannot process that input. Please provide a plain-text repository question.",
    "INPUT_TOO_LONG": "I cannot process that request because it exceeds the input length limit.",
    "UNSAFE_REQUEST": "I cannot help with requests to expose credentials, damage systems, or bypass safety controls.",
    "PROMPT_INJECTION": "I cannot follow instructions that attempt to override the application's rules or retrieved evidence.",
    "OUT_OF_SCOPE": "I can only answer questions about this repository's code, architecture, tests, and documentation.",
    "INSUFFICIENT_CONTEXT": "I do not have sufficient repository evidence to answer that question reliably.",
    "UNSUPPORTED_OUTPUT": "I could not produce an answer that is sufficiently supported by the retrieved repository context.",
    "UNTRUSTED_CONTEXT": "Direct context is disabled. Repository evidence must come from the retrieval service.",
    "UNSUPPORTED_MODEL": "The requested model is not enabled for this application.",
}

SCOPE_TERMS = {
    "api", "application", "architecture", "auth", "authentication", "bcrypt",
    "bug", "calculate", "call", "class", "code", "component", "context",
    "database", "dependency", "documentation", "embedding", "fee", "file",
    "function", "implementation", "index", "login", "model", "module", "payment",
    "pipeline", "rag", "refactor", "registration", "register", "repository",
    "response", "retrieval", "service", "session", "stripe", "test", "token",
    "transaction", "user", "vector",
}
INJECTION_PATTERNS = (
    r"ignore (?:all |any )?(?:previous|prior|system) instructions?",
    r"reveal (?:the )?system prompt",
    r"developer message",
    r"jailbreak",
    r"bypass (?:the )?(?:guardrail|safety|policy)",
    r"pretend (?:the )?(?:rules|instructions) do not apply",
)
UNSAFE_PATTERNS = (
    r"(?:steal|extract|dump|reveal).{0,30}(?:password|credential|secret|hash|token|key)",
    r"(?:delete|destroy|wipe).{0,30}(?:system|repository|files?|database)",
    r"(?:ransomware|keylogger|credential stuffing)",
)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "does", "for",
    "from", "how", "i", "if", "in", "is", "it", "me", "of", "on", "or",
    "that", "the", "this", "to", "what", "when", "where", "which", "with",
    "would", "write", "explain", "suggest", "create", "show",
}
EVIDENCE_INTENT_WORDS = {
    "according", "across", "after", "algorithm", "already", "before", "change",
    "code", "component", "could", "creation", "data", "decimal", "defined",
    "depend", "do", "during", "end", "error", "exist", "external", "field",
    "file", "function", "go", "handle", "handling", "happen", "implement",
    "improved", "involved", "library", "look", "message", "missing", "named",
    "negative", "new", "numeric", "object", "only", "otherwise", "persistence",
    "positive", "processed", "python", "queried", "raise", "receive", "record",
    "refactor", "repository", "request", "return", "send", "separated", "service",
    "sign", "store", "submit", "table", "testability", "time", "touch", "trace",
    "true", "two", "up", "use", "validation", "valueerror", "work", "workflow",
    "wrong", "you", "affect", "default", "through", "call", "compare",
    "include",
}


@dataclass
class GuardrailDecision:
    allowed: bool
    stage: str
    reason_code: str | None = None
    message: str | None = None
    checks: list[str] = field(default_factory=list)

    def as_dict(self, **extra):
        value = {
            "enabled": True,
            "allowed": self.allowed,
            "stage": self.stage,
            "reason_code": self.reason_code,
            "checks": self.checks,
        }
        value.update(extra)
        return value


def _words(value: str) -> set[str]:
    aliases = {
        "authentication": "auth", "authenticated": "auth", "registration": "register",
        "libraries": "library",
        "database": "db", "tables": "table", "models": "model", "fields": "field",
        "stored": "store", "used": "use", "using": "use", "implemented": "implement",
        "changes": "change", "compared": "compare", "comparing": "compare",
        "calls": "call", "called": "call", "included": "include", "including": "include",
        "affected": "affect", "messages": "message", "sends": "send", "submits": "submit",
        "happens": "happen", "touched": "touch", "components": "component",
    }
    words = set()
    for raw in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", value):
        word = raw.lower()
        word = aliases.get(
            word,
            word[:-1]
            if len(word) > 4 and word.endswith("s") and not word.endswith("ss")
            else word,
        )
        words.add(word)
    return words


def validate_input(prompt: object) -> GuardrailDecision:
    if not isinstance(prompt, str) or not prompt.strip():
        return GuardrailDecision(False, "input", "INVALID_INPUT", REFUSALS["INVALID_INPUT"])
    if len(prompt) > MAX_PROMPT_CHARS:
        return GuardrailDecision(False, "input", "INPUT_TOO_LONG", REFUSALS["INPUT_TOO_LONG"], ["length_limit"])
    if any(ord(char) < 32 and char not in "\n\r\t" for char in prompt):
        return GuardrailDecision(False, "input", "INVALID_INPUT", REFUSALS["INVALID_INPUT"], ["plain_text"])
    lowered = prompt.lower()
    if any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS):
        return GuardrailDecision(False, "input", "PROMPT_INJECTION", REFUSALS["PROMPT_INJECTION"], ["prompt_injection"])
    if any(re.search(pattern, lowered) for pattern in UNSAFE_PATTERNS):
        return GuardrailDecision(False, "input", "UNSAFE_REQUEST", REFUSALS["UNSAFE_REQUEST"], ["unsafe_intent"])
    has_code_reference = bool(re.search(r"\b[A-Za-z_]\w*(?:_[A-Za-z0-9_]+|\s*\()", prompt))
    if not (_words(prompt) & SCOPE_TERMS) and not has_code_reference:
        return GuardrailDecision(False, "input", "OUT_OF_SCOPE", REFUSALS["OUT_OF_SCOPE"], ["repository_scope"])
    return GuardrailDecision(True, "input", checks=["length_limit", "plain_text", "repository_scope", "safety"])


def validate_retrieval(prompt: str, matches: list[dict]) -> GuardrailDecision:
    if not matches:
        return GuardrailDecision(False, "retrieval", "INSUFFICIENT_CONTEXT", REFUSALS["INSUFFICIENT_CONTEXT"], ["has_results"])
    top_score = float(matches[0].get("score", 0.0))
    prompt_terms = _words(prompt) - STOP_WORDS - EVIDENCE_INTENT_WORDS
    evidence_terms = _words(" ".join(
        f"{match.get('file', '')} {match.get('text', '')}" for match in matches
    ))
    lexical_overlap = prompt_terms & evidence_terms
    creative_request = bool(re.search(r"\b(write|generate|create|refactor|suggest|unit test)\b", prompt.lower()))
    code_references = set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", prompt))
    code_reference_found = creative_request or not code_references or code_references <= evidence_terms
    overlap_ratio = len(lexical_overlap) / len(prompt_terms) if prompt_terms else 0.0
    enough_overlap = bool(lexical_overlap) if creative_request else overlap_ratio > 0.5
    if top_score < MIN_RETRIEVAL_SCORE or not enough_overlap or not code_reference_found:
        return GuardrailDecision(
            False,
            "retrieval",
            "INSUFFICIENT_CONTEXT",
            REFUSALS["INSUFFICIENT_CONTEXT"],
            ["minimum_similarity", "evidence_overlap"],
        )
    return GuardrailDecision(True, "retrieval", checks=["has_results", "minimum_similarity", "evidence_overlap"])


def _known_call_edges(context: str) -> tuple[set[str], set[tuple[str, str]]]:
    source = re.sub(r"(?m)^.* \(chunk \d+\):\s*$", "", context)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set(), set()
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    edges = set()
    for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
        for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
            if isinstance(call.func, ast.Name):
                edges.add((function.name, call.func.id))
            elif isinstance(call.func, ast.Attribute):
                edges.add((function.name, call.func.attr))
    return functions, edges


def unsupported_relationships(answer: str, context: str) -> list[str]:
    """Flag explicit function-call relationships not present in the retrieved code."""
    functions, edges = _known_call_edges(context)
    plain = answer.replace("`", "")
    claims = []
    patterns = (
        (r"\b(\w+)\(\).*?\b(?:calls?|uses?|invokes?)\b.*?\b(\w+)\(\)", False),
        (r"\b(\w+)\(\).*?\b(?:is\s+)?(?:also\s+)?(?:used|called|invoked)\s+(?:by|in)\b.*?\b(\w+)\(\)", True),
    )
    for sentence in re.split(r"(?<=[.!?])\s+", plain):
        for pattern, reverse in patterns:
            for first, second in re.findall(pattern, sentence, flags=re.IGNORECASE):
                source, target = (second, first) if reverse else (first, second)
                if source in functions and target in functions and (source, target) not in edges:
                    claims.append(f"{source}->{target}")
    read_tables = {
        name.lower() + ("" if name.lower().endswith("s") else "s")
        for name in re.findall(r"\bdb\.query\(\s*([A-Za-z_]\w*)", context)
    }
    write_tables = {
        name.lower()
        for name in re.findall(r"\bdb\.insert\(\s*[\"']([A-Za-z_]\w*)[\"']", context)
    }
    for sentence in re.split(r"(?<=[.!?])\s+", plain):
        for table in re.findall(
            r"\b(?:retrieve\w*|read\w*|quer(?:y|ies|ied))\b.*?\b([A-Za-z_]\w*)\s+table\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            if table.lower() not in read_tables:
                claims.append(f"read-table:{table.lower()}")
        for table in re.findall(
            r"\b(?:write\w*|insert\w*|store[ds]?)\b.*?\b([A-Za-z_]\w*)\s+table\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            if table.lower() not in write_tables:
                claims.append(f"write-table:{table.lower()}")
    section_parts = re.split(r"(?m)^.* \(chunk \d+\):\s*$", context)
    section_terms = [_words(part) - STOP_WORDS - EVIDENCE_INTENT_WORDS for part in section_parts if part.strip()]
    if len(section_terms) > 1:
        all_terms = set().union(*section_terms)
        relation_pattern = r"\b(use[ds]?|pass(?:es|ed)?|send[ds]?|identif\w*|authenticate(?:s|d|ing)?|depend\w*|call\w*|includ(?:e|es|ed|ing)|stor(?:e|es|ed|ing))\b"
        generic = {
            "answer", "argument", "client", "code", "function", "generate", "hashed",
            "place", "result", "step", "system", "user",
        }
        for sentence in re.split(r"(?<=[.!?])\s+", plain):
            if not re.search(relation_pattern, sentence, re.IGNORECASE):
                continue
            terms = (_words(sentence) - STOP_WORDS - EVIDENCE_INTENT_WORDS - generic) & all_terms
            specific = {term for term in terms if len(term) >= 4}
            if len(specific) >= 2 and not any(specific <= terms_in_section for terms_in_section in section_terms):
                claims.append("cross-context:" + ",".join(sorted(specific)))
            novel = (
                _words(sentence)
                - STOP_WORDS
                - EVIDENCE_INTENT_WORDS
                - generic
                - all_terms
            )
            novel_specific = {term for term in novel if len(term) >= 5}
            if len(novel_specific) >= 2:
                claims.append("unsupported-concepts:" + ",".join(sorted(novel_specific)))
    return sorted(set(claims))


def unsupported_claims(answer: str, context: str, allow_proposals: bool = False) -> list[str]:
    """Return code symbols/files claimed by a factual answer but absent from evidence."""
    generated_symbols = set(re.findall(r"(?m)^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)", answer))
    prose = re.sub(r"```.*?```", "", answer, flags=re.DOTALL)
    identifiers = {
        item.rstrip("(").strip()
        for item in re.findall(r"\b[A-Za-z_]\w*\(", prose)
    }
    identifiers -= {"if", "for", "while", "print", "return"}
    files = set(re.findall(r"\b[\w.-]+\.(?:py|js|ts|md|json|ya?ml)\b", prose))
    unsupported = []
    for claim in identifiers | files:
        if claim in context or claim in generated_symbols:
            continue
        if allow_proposals:
            sentence = next((part for part in re.split(r"(?<=[.!?])\s+", prose) if claim in part), "")
            if re.search(r"\b(could|would|propose|suggest|introduce|new|example|extract)\b", sentence, re.IGNORECASE):
                continue
        unsupported.append(claim)
    return sorted(unsupported)


def validate_output(prompt: str, answer: object, context: str) -> GuardrailDecision:
    if not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_RESPONSE_CHARS:
        return GuardrailDecision(False, "output", "UNSUPPORTED_OUTPUT", REFUSALS["UNSUPPORTED_OUTPUT"], ["nonempty", "length_limit"])
    if any(ord(char) < 32 and char not in "\n\r\t" for char in answer) or answer.count("```") % 2:
        return GuardrailDecision(False, "output", "UNSUPPORTED_OUTPUT", REFUSALS["UNSUPPORTED_OUTPUT"], ["response_format"])
    lowered = answer.lower()
    if "i do not have sufficient repository evidence" in lowered or "context does not contain" in lowered:
        return GuardrailDecision(False, "output", "INSUFFICIENT_CONTEXT", REFUSALS["INSUFFICIENT_CONTEXT"], ["model_refusal"])
    creative_request = bool(re.search(r"\b(write|generate|create|refactor|suggest|unit test)\b", prompt.lower()))
    code_generation_request = bool(
        re.search(r"\b(?:write|generate|create)\b.*\b(?:code|function|test)\b|\bunit test\b", prompt, re.IGNORECASE)
    )
    if code_generation_request and not re.fullmatch(
        r"```(?:[A-Za-z0-9_+.-]+)?[ \t]*\r?\n?.*?```", answer.strip(), re.DOTALL
    ):
        return GuardrailDecision(
            False,
            "output",
            "UNSUPPORTED_OUTPUT",
            REFUSALS["UNSUPPORTED_OUTPUT"],
            ["response_format"],
        )
    claims = unsupported_claims(answer, context, allow_proposals=creative_request)
    relationships = unsupported_relationships(answer, context)
    if claims or relationships:
        return GuardrailDecision(False, "output", "UNSUPPORTED_OUTPUT", REFUSALS["UNSUPPORTED_OUTPUT"], ["grounded_code_claims"])
    answer_terms = _words(answer) - STOP_WORDS
    prompt_terms = _words(prompt) - STOP_WORDS
    context_terms = _words(context) - STOP_WORDS
    if not (answer_terms & (prompt_terms | context_terms)):
        return GuardrailDecision(False, "output", "UNSUPPORTED_OUTPUT", REFUSALS["UNSUPPORTED_OUTPUT"], ["relevance"])
    return GuardrailDecision(True, "output", checks=["nonempty", "length_limit", "response_format", "relevance", "grounded_code_claims"])
