from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import rag
from .pipeline import review_code

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if rag.count() == 0:
        print(f"Ingested {rag.ingest_policies()} policies into ChromaDB")
    yield


app = FastAPI(title="PolicyGuard", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ValidateRequest(BaseModel):
    code: str


@app.get("/", response_class=HTMLResponse)
def ui():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.post("/validate")
async def validate(req: ValidateRequest):
    return await review_code(req.code)