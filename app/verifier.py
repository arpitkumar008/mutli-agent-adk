"""Deterministic verification: no LLM involved."""
import json
import re
from pydantic import BaseModel

from . import rag


def _parse(raw) -> dict:
    if isinstance(raw, BaseModel):
        return raw.model_dump()
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        return json.loads(cleaned)
    raise ValueError("validator produced no output")


def _norm(s: str) -> str:
    return " ".join(s.split())


def verify(code: str, state: dict) -> dict:
    store = rag.policy_map()                       # ground truth from ChromaDB
    retrieved = list(state.get("retrieved_ids", []))

    try:
        findings = _parse(state.get("validation"))["findings"]
    except Exception as e:
        return {"status": "UNVERIFIED", "summary": f"Validator output unusable: {e}",
                "findings": [], "integrity": {"retrieval_happened": bool(retrieved)}}

    cited = [f["policy_id"] for f in findings]
    code_n = _norm(code)

    integrity = {
        "retrieval_happened": bool(retrieved),
        "unknown_policies_cited": sorted(set(cited) - set(store)),
        "policies_cited_but_not_retrieved": sorted((set(cited) & set(store)) - set(retrieved)),
        "retrieved_but_not_checked": sorted(set(retrieved) - set(cited)),
        "fail_evidence_not_found_in_code": [
            f["policy_id"] for f in findings
            if f["verdict"] == "FAIL" and (not f["evidence"] or _norm(f["evidence"]) not in code_n)
        ],
    }
    integrity_ok = (
        integrity["retrieval_happened"]
        and not integrity["unknown_policies_cited"]
        and not integrity["policies_cited_but_not_retrieved"]
        and not integrity["retrieved_but_not_checked"]
    )

    enriched = [
        {"policy_id": f["policy_id"],
         "policy_title": store.get(f["policy_id"], {}).get("title", "UNKNOWN"),
         "verdict": f["verdict"], "reason": f["reason"], "evidence": f["evidence"]}
        for f in findings
    ]
    fails = [f for f in enriched if f["verdict"] == "FAIL"]

    if not integrity_ok:
        status, summary = "UNVERIFIED", "LLM did not use the retrieved policies correctly; result is not trusted."
    elif fails:
        status, summary = "FAILED", f"{len(fails)} of {len(enriched)} policies violated."
    else:
        status, summary = "PASSED", f"All {len(enriched)} retrieved policies passed."

    return {"status": status, "summary": summary, "findings": enriched, "integrity": integrity}