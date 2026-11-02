# PolicyGuard

An AI system that checks whether a proposed code change violates an organization's engineering policies before it is merged.

**Stack:** Google ADK (2 agents) · FastAPI · ChromaDB (RAG, local embeddings) · LiteLLM (OpenRouter) · input + output guardrails · deterministic verifier

## How it works

```
Code input
  -> Input guardrail        (blocks empty / huge / prompt-injection input; injection triggers policy re-ingest)
  -> Agent 1: Retriever     (RAG search over ChromaDB, policies chunked per policy ID)
  -> Agent 2: Validator     (PASS / FAIL per retrieved policy, with reason + evidence)
  -> Deterministic verifier (proves the LLM used only the retrieved policies)
  -> Output guardrail       (redacts secrets in the report)
  -> PASSED / FAILED / UNVERIFIED / BLOCKED
```

## Project structure

```
policy-guard/
├── .env
├── requirements.txt
├── README.md
├── policies/
│   └── engineering_policies.md      # add your .md / .txt / .pdf policy files here
└── app/
    ├── __init__.py
    ├── config.py
    ├── rag.py
    ├── guardrails.py
    ├── agents.py
    ├── verifier.py
    ├── pipeline.py
    ├── main.py
    └── static/
        ├── index.html
        ├── style.css
        └── app.js
```

Policy files must use headings in this format (one chunk per policy ID):

```
POLICY SEC-001: No hardcoded secrets
Passwords, API keys and tokens must never be written in source code.
```

## Requirements

- Python 3.10+
- An [OpenRouter](https://openrouter.ai) API key

`requirements.txt`:

```
google-adk[extensions]
litellm
mcp
fastapi
uvicorn[standard]
chromadb
pypdf
python-dotenv
pydantic
```

## Setup and run

### Windows (PowerShell)

```powershell
cd policy-guard
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

If PowerShell blocks activation, run this once and activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Windows (Command Prompt)

```cmd
cd policy-guard
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### macOS / Linux

```bash
cd policy-guard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Configuration (`.env`)

Create a file named `.env` (not `.env.txt`) in the project root:

```
OPENROUTER_API_KEY=your_openrouter_key_here
LLM_MODEL=openrouter/openai/gpt-4o-mini
TOP_K=5
```

- The model string is `openrouter/` followed by the OpenRouter model ID.
- Use a model that supports **tool calling** (the Retriever agent calls the RAG tool). Free `:free` models are often rate-limited and unreliable at tool calling.
- Restart the server after editing `.env`; `--reload` does not re-read it.

## Using the app

Open **http://127.0.0.1:8000/**, paste code into the chat box, and press **Validate** (or Ctrl+Enter).

The first start downloads the local embedding model (~80 MB) and prints `Ingested N policies into ChromaDB`.

Only two endpoints exist:

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Chat UI |
| POST | `/validate` | Body: `{"code": "..."}` returns the report |

Command-line test:

```powershell
curl -X POST http://127.0.0.1:8000/validate -H "Content-Type: application/json" -d "{\"code\": \"password = 'admin123'\"}"
```

## Result statuses

| Status | Meaning |
|---|---|
| PASSED | All retrieved policies passed and integrity checks succeeded |
| FAILED | At least one policy violated (reason + evidence shown) |
| UNVERIFIED | The model misused policies, or the model call / output failed |
| BLOCKED | Input guardrail stopped it (injection also re-ingests policies, 60 s cooldown) |

## Common tasks

**Add or change policies** — edit files in `policies/`, then restart the server. If the policy store already has data it is not rebuilt automatically, so delete the `chroma_db/` folder first:

```powershell
Remove-Item -Recurse -Force chroma_db
uvicorn app.main:app --reload
```

macOS / Linux: `rm -rf chroma_db`

**Switch model** — change only `LLM_MODEL` in `.env` and restart.

**Deactivate the virtual environment** — `deactivate`

## Troubleshooting

| Problem | Fix |
|---|---|
| `LLM Provider NOT provided` | `LLM_MODEL` is missing the `openrouter/` prefix, or a stale Windows variable overrides `.env`. Check with `echo $env:LLM_MODEL` and clear with `Remove-Item Env:LLM_MODEL` |
| `LiteLLM support requires: pip install google-adk[extensions]` | `pip install "google-adk[extensions]"` |
| `No module named 'mcp'` | `pip install mcp` |
| `AuthenticationError` | Wrong or missing `OPENROUTER_API_KEY`; restart the server after fixing `.env` |
| `UNVERIFIED` with `retrieval_happened: false` | The model did not call the RAG tool; switch to a model with reliable tool calling |
| `UNVERIFIED` with "Validator output unusable" | The model did not return valid JSON; try a stronger model |
| `404` on `/docs` | Expected; docs are disabled. Use `/` |
| Old UI after changes | Hard refresh with Ctrl+F5 |
