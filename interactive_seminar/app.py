from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from interactive_seminar.executor import execute_block
from interactive_seminar.gigachat_runner import GigaChatRunner
from interactive_seminar.notebook_loader import load_manifest
from interactive_seminar.schemas import SeminarManifest


class ConnectionTestRequest(BaseModel):
    credentials: str
    model: str


class RunBlockRequest(BaseModel):
    credentials: str
    model: str
    overrides: dict[str, object] = Field(default_factory=dict)


class SandboxRequest(BaseModel):
    credentials: str
    model: str
    messages: list[dict[str, str]] = Field(default_factory=list)
    system_prompt: str = ""
    prefill: str = ""
    stop_sequences: list[str] = Field(default_factory=list)


def create_app(
    *,
    manifest: SeminarManifest | None = None,
    runner=None,
) -> FastAPI:
    repo_root = Path(__file__).resolve().parents[1]
    templates = Jinja2Templates(directory=str(repo_root / "interactive_seminar" / "templates"))
    app = FastAPI()
    app.state.manifest = manifest or _load_default_manifest()
    app.state.runner = runner or GigaChatRunner()
    app.mount(
        "/static",
        StaticFiles(directory=str(repo_root / "interactive_seminar" / "static")),
        name="static",
    )

    @app.get("/")
    def index(request: Request):
        return templates.TemplateResponse(request, "index.html", {})

    @app.get("/api/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/manifest")
    def get_manifest() -> SeminarManifest:
        return app.state.manifest

    @app.post("/api/session/test-connection")
    def test_connection(request: ConnectionTestRequest) -> dict[str, str]:
        try:
            response = app.state.runner.run(
                credentials=request.credentials,
                model=request.model,
                prompt_or_messages="ping",
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "ok", "response": response}

    @app.post("/api/run/block/{block_id}")
    def run_block(block_id: str, request: RunBlockRequest):
        try:
            block = app.state.manifest.block(block_id)
            return execute_block(
                block,
                request.overrides,
                app.state.runner,
                credentials=request.credentials,
                model=request.model,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/run/sandbox")
    def run_sandbox(request: SandboxRequest) -> dict[str, object]:
        try:
            response = app.state.runner.run(
                credentials=request.credentials,
                model=request.model,
                prompt_or_messages=request.messages,
                system_prompt=request.system_prompt,
                prefill=request.prefill,
                stop_sequences=request.stop_sequences,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "messages": request.messages,
            "system_prompt": request.system_prompt,
            "prefill": request.prefill,
            "response": response,
        }

    return app


def _load_default_manifest() -> SeminarManifest:
    repo_root = Path(__file__).resolve().parents[1]
    return load_manifest(str(repo_root / "PE_seminar.ipynb"), str(repo_root / "hints.py"))
