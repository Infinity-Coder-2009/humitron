#!/usr/bin/env python3
"""
FastAPI server for Humitron desktop backend.
Exposes REST endpoints for the Tauri frontend.
"""

import asyncio
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from humitron.agent import ReActAgent
from humitron.config.loader import Config, get_config, load_config
from humitron.tools.registry import TOOLS, TOOL_SCHEMAS
from humitron.memory.conversation import ConversationMemory
from humitron.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

# Global state
agent: Optional[ReActAgent] = None
sessions: Dict[str, Dict] = {}
current_config: Config = get_config()


class ChatRequest(BaseModel):
    prompt: str
    session_id: str
    model: str = "llama3.2"
    temperature: float = 0.7
    max_steps: int = 20
    workspace: str = "."
    provider: Optional[str] = None
    api_key: Optional[str] = None


class SessionCreate(BaseModel):
    name: str
    model: Optional[str] = None
    workspace: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None


class ConfigUpdate(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_steps: Optional[int] = None
    workspace: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global agent, current_config

    # Setup logging
    setup_logging(log_level=current_config.log_level)

    # Initialize default agent
    agent = ReActAgent(
        model=current_config.model,
        max_steps=current_config.max_steps,
        workspace=Path(current_config.workspace_path),
        temperature=current_config.temperature,
    )

    logger.info("Backend started successfully")
    yield

    # Cleanup
    if agent:
        agent.close()
    logger.info("Backend shutting down")


app = FastAPI(
    title="Humitron Backend",
    description="Local-first AI Agent API with multi-provider support",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS for Tauri frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost", "https://tauri.localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_or_create_agent(
    model: str,
    max_steps: int,
    workspace: str,
    temperature: float,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
) -> ReActAgent:
    """Get or create agent with specified config."""
    global agent, current_config

    # Check if we need to recreate agent
    if (agent is None or
        agent.model != model or
        agent.max_steps != max_steps or
        agent.temperature != temperature or
        agent.provider_name != provider or
        agent.api_key != api_key or
        str(agent.workspace_dir) != str(Path(workspace).resolve())):
        agent = ReActAgent(
            model=model,
            max_steps=max_steps,
            workspace=Path(workspace),
            temperature=temperature,
            provider=provider,
            api_key=api_key,
        )
    return agent


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    import httpx

    ollama_running = False
    models = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                ollama_running = True
                data = resp.json()
                models = data.get("models", [])
    except Exception:
        pass

    return {
        "ollama_running": ollama_running,
        "models": models,
        "backend_running": agent is not None,
        "config": {
            "model": current_config.model,
            "workspace": current_config.workspace_path,
        },
    }


@app.get("/models")
async def list_models():
    """List available Ollama models."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
    return {"models": []}


@app.post("/models/pull")
async def pull_model(request: Request):
    """Pull a model from Ollama."""
    import httpx
    data = await request.json()
    model_name = data.get("name", "")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/pull",
                json={"name": model_name, "stream": False},
            )
            if resp.status_code == 200:
                return {"message": f"Model {model_name} pulled successfully"}
            else:
                raise HTTPException(status_code=resp.status_code, detail="Failed to pull model")
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="Pull timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: ChatRequest):
    """Stream chat response using Server-Sent Events."""
    # Get or create agent with request config
    ag = get_or_create_agent(
        model=request.model,
        max_steps=request.max_steps,
        workspace=request.workspace,
        temperature=request.temperature,
        provider=request.provider,
        api_key=request.api_key,
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        session_id = request.session_id

        # Get or create session memory
        if session_id not in sessions:
            sessions[session_id] = {
                "memory": ConversationMemory(max_tokens=8000),
                "created_at": datetime.now().isoformat(),
            }
            sessions[session_id]["memory"].add_message("system", ag.system_prompt)

        memory = sessions[session_id]["memory"]

        # Add user message
        memory.add_message("user", request.prompt)

        total_input_tokens = 0
        total_output_tokens = 0

        try:
            async for chunk in ag.run_stream(request.prompt):
                # Track tokens from agent's internal counting
                yield f"data: {json.dumps(chunk)}\n\n"

                if chunk["type"] == "done":
                    cost_data = chunk["data"].get("cost", {})
                    total_input_tokens = cost_data.get("input_tokens", 0)
                    total_output_tokens = cost_data.get("output_tokens", 0)
                    return
                elif chunk["type"] == "error":
                    return

        except Exception as e:
            logger.exception("Chat error")
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/sessions")
async def list_sessions():
    """List all conversation sessions."""
    return {
        "sessions": [
            {
                "id": sid,
                "name": data.get("name", f"Session {sid[:8]}"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at", data.get("created_at")),
            }
            for sid, data in sessions.items()
        ]
    }


@app.post("/sessions")
async def create_session(request: SessionCreate):
    """Create a new session."""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "name": request.name,
        "model": request.model or current_config.model,
        "workspace": request.workspace or current_config.workspace_path,
        "provider": request.provider,
        "api_key": request.api_key,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "memory": ConversationMemory(max_tokens=8000),
    }
    sessions[session_id]["memory"].add_message("system", agent.system_prompt if agent else "")
    return {"session_id": session_id}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get messages for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    memory = sessions[session_id]["memory"]
    return {"messages": memory.get_messages()}


@app.post("/config")
async def update_config(request: ConfigUpdate):
    """Update backend configuration."""
    global current_config, agent

    updates = request.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if hasattr(current_config, key):
            setattr(current_config, key, value)

    # Recreate agent if model or workspace changed
    if any(k in updates for k in ["model", "workspace", "max_steps", "temperature", "provider", "api_key"]):
        agent = ReActAgent(
            model=current_config.model,
            max_steps=current_config.max_steps,
            workspace=Path(current_config.workspace_path),
            temperature=current_config.temperature,
            provider=updates.get("provider"),
            api_key=updates.get("api_key"),
        )

    return {"message": "Configuration updated", "config": current_config.to_dict()}


@app.get("/config")
async def get_config_endpoint():
    """Get current configuration."""
    return current_config.to_dict()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Humitron Backend Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    parser.add_argument("--log-level", default="INFO", help="Log level")

    args = parser.parse_args()

    global current_config
    current_config.workspace_path = args.workspace
    current_config.log_level = args.log_level

    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()