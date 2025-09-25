"""FastAPI application exposing the virtual organization dashboard."""
from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .database import Database
from .organization import Organization

app = FastAPI(title="Sjuk Autonomous Org")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
async def startup() -> None:
    db_path = Path("data/org.db")
    app.state.db = Database(str(db_path))
    app.state.org = Organization(app.state.db)
    app.state.simulation_task = asyncio.create_task(app.state.org.run())


@app.on_event("shutdown")
async def shutdown() -> None:
    task = getattr(app.state, "simulation_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    db = getattr(app.state, "db", None)
    if db:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/agents")
async def get_agents() -> Dict[str, object]:
    agents = app.state.db.fetch_agents()
    return {"agents": agents}


@app.get("/api/projects")
async def get_projects() -> Dict[str, object]:
    projects = app.state.db.fetch_projects()
    return {"projects": projects}


@app.get("/api/messages")
async def get_messages(limit: int = 50) -> Dict[str, object]:
    messages = app.state.db.fetch_recent_messages(limit=limit)
    return {"messages": messages}


@app.get("/api/finance")
async def get_finance(limit: int = 20) -> Dict[str, object]:
    history = app.state.db.fetch_finance_history(limit=limit)
    return {"history": history, "cash": history[0]["cash"] if history else 0.0}


@app.post("/api/interview")
async def interview(payload: Dict[str, str]) -> Dict[str, str]:
    agent_name = payload.get("agent")
    question = payload.get("question", "")
    if not agent_name:
        raise HTTPException(status_code=400, detail="agent is required")
    reply = app.state.org.handle_interview(agent_name, question)
    return {"reply": reply}
