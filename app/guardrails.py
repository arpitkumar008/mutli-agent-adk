"""Exactly two guardrails: input and output."""
import re
from dataclasses import dataclass

from .config import MAX_CODE_CHARS


@dataclass
class GuardrailResult:
    ok: bool
    reason: str = ""
    injection: bool = False


INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules|policies)",
    r"disregard (the |all )?(policies|rules|instructions)",
    r"(mark|report|return|say) (this|it|everything) (as )?(pass|passed|compliant)",
    r"you are now",
    r"reveal (your )?(system )?prompt",
]


def input_guardrail(code: str) -> GuardrailResult:
    if not code or len(code.strip()) < 5:
        return GuardrailResult(False, "Input is empty or too short.")
    if len(code) > MAX_CODE_CHARS:
        return GuardrailResult(False, f"Input exceeds {MAX_CODE_CHARS} characters.")
    for pat in INJECTION_PATTERNS:
        if re.search(pat, code, re.IGNORECASE):
            return GuardrailResult(False, "Possible prompt injection detected in the submitted code.", injection=True)
    return GuardrailResult(True)


SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "[REDACTED_API_KEY]"),
    (re.compile(r"(?i)(password|passwd|secret|token|api_?key)(\s*[=:]\s*)(['\"])[^'\"]+\3"),
     r"\1\2\3[REDACTED]\3"),
]


def _redact(text: str) -> str:
    for pat, repl in SECRET_PATTERNS:
        text = pat.sub(repl, text)
    return text[:800]


def output_guardrail(report: dict) -> dict:
    """Validate the report shape and redact secrets echoed back from the code."""
    if report.get("status") not in {"PASSED", "FAILED", "UNVERIFIED"}:
        report["status"] = "UNVERIFIED"
    for f in report.get("findings", []):
        f["reason"] = _redact(str(f.get("reason", "")))
        f["evidence"] = _redact(str(f.get("evidence", "")))
        if f.get("verdict") not in {"PASS", "FAIL"}:
            f["verdict"] = "FAIL"
    return report