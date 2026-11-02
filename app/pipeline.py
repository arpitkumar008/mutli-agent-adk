import asyncio
import time
import uuid
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from . import rag
from .agents import root_agent
from .config import APP_NAME
from .guardrails import input_guardrail, output_guardrail
from .verifier import verify

session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

REINGEST_COOLDOWN = 60  
_last_reingest = 0.0


async def _reingest_policies() -> str:
    global _last_reingest
    if time.time() - _last_reingest < REINGEST_COOLDOWN:
        return "Policy re-ingest skipped (cooldown active)."
    _last_reingest = time.time()
    try:
        n = await asyncio.to_thread(rag.ingest_policies)
        return f"Policies re-ingested from the policies folder ({n} policies)."
    except Exception as e:
        return f"Policy re-ingest failed: {e}"


async def _run_agents(code: str) -> dict:
    user_id, session_id = "api_user", str(uuid.uuid4())
    await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
    message = types.Content(
        role="user",
        parts=[types.Part(text=f"Review this code change:\n```\n{code}\n```")],
    )
    async for _ in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        pass
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id)
    return dict(session.state)


async def review_code(code: str) -> dict:
    # 1) input guardrail
    g = input_guardrail(code)
    if not g.ok:
        action = await _reingest_policies() if g.injection else ""
        return {"status": "BLOCKED", "summary": g.reason, "findings": [],
                "integrity": {}, "action": action}
    # 2) retriever agent -> validator agent
    state = await _run_agents(code)
    # 3) deterministic verification
    report = verify(code, state)
    # 4) output guardrail
    return output_guardrail(report)