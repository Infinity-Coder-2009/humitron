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


class ChatResponse(BaseModel):
    type: str  # "thinking", "tool_call", "tool_result", "content", "done", "error"
    data: Dict[str, Any]


class SessionCreate(BaseModel):
    name: str
    model: Optional[str] = None
    workspace: Optional[str] = None


class ConfigUpdate(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_steps: Optional[int] = None
    workspace: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global agent, current_config
    
    # Setup logging
    setup_logging(log_level=current_config.log_level)
    
    # Initialize agent
    agent = ReActAgent(
        model=current_config.model,
        max_steps=current_config.max_steps,
        workspace=Path(current_config.workspace_path),
        temperature=current_config.temperature,
    )
    
    logger.info("Backend started successfully")
    yield
    
    logger.info("Backend shutting down")


app = FastAPI(
    title="Humitron Backend",
    description="Local-first AI Agent API",
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
    global agent
    
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Update agent config if needed
    if (agent.model != request.model or 
        agent.max_steps != request.max_steps or
        agent.temperature != request.temperature):
        agent = ReActAgent(
            model=request.model,
            max_steps=request.max_steps,
            workspace=Path(request.workspace),
            temperature=request.temperature,
        )
    
    async def event_generator() -> AsyncGenerator[str, None]:
        session_id = request.session_id
        
        # Get or create session memory
        if session_id not in sessions:
            sessions[session_id] = {
                "memory": ConversationMemory(max_tokens=8000),
                "created_at": datetime.now().isoformat(),
            }
            # Add system prompt
            sessions[session_id]["memory"].add_message("system", agent.system_prompt)
        
        memory = sessions[session_id]["memory"]
        
        # Add user message
        memory.add_message("user", request.prompt)
        
        # Stream response
        step = 0
        total_input_tokens = 0
        total_output_tokens = 0
        
        try:
            while step < request.max_steps:
                step += 1
                
                # Check summarization
                if memory.should_summarize():
                    memory.summarize_middle(agent.ollama)
                
                # Get LLM response
                response = agent.ollama.chat(
                    memory.get_messages(),
                    tools=TOOL_SCHEMAS
                )
                
                assistant_message = response.get("message", {})
                content = assistant_message.get("content", "")
                
                # Estimate tokens
                input_tokens = sum(len(m.get("content", "")) // 4 for m in memory.get_messages())
                output_tokens = len(content) // 4
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                
                memory.add_message("assistant", content)
                
                # Parse tool calls
                tool_calls = agent._parse_tool_calls(content)
                
                if not tool_calls and content.strip().startswith("{"):
                    try:
                        data = json.loads(content)
                        if "name" in data and "arguments" in data:
                            tool_calls = [type('ToolCall', (), {"name": data["name"], "arguments": data["arguments"]})()]
                        elif "tool_calls" in data:
                            tool_calls = [type('ToolCall', (), {"name": tc["name"], "arguments": tc["arguments"]})() for tc in data.get("tool_calls", [])]
                    except json.JSONDecodeError:
                        pass
                
                if not tool_calls:
                    # Final answer
                    yield f"data: {json.dumps({'type': 'content', 'data': {'content': content}})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'data': {'cost': {'total_tokens': total_input_tokens + total_output_tokens, 'input_tokens': total_input_tokens, 'output_tokens': total_output_tokens, 'estimated_cost': 0.0}}})}\n\n"
                    return
                
                # Send thinking
                if content and "tool_calls" not in content:
                    yield f"data: {json.dumps({'type': 'thinking', 'data': {'thinking': content}})}\n\n"
                
                # Execute tools
                for tool_call in tool_calls:
                    tool_call_id = str(uuid.uuid4())
                    
                    yield f"data: {json.dumps({'type': 'tool_call', 'data': {'tool_call_id': tool_call_id, 'name': tool_call.name, 'arguments': tool_call.arguments}})}\n\n"
                    
                    # Execute tool
                    tool_func = TOOLS.get(tool_call.name)
                    if tool_func:
                        result = tool_func(**tool_call.arguments)
                        tool_result = {
                            "success": result.success,
                            "output": result.output if result.success else result.error,
                        }
                    else:
                        tool_result = {
                            "success": False,
                            "output": f"Unknown tool: {tool_call.name}",
                        }
                    
                    yield f"data: {json.dumps({'type': 'tool_result', 'data': {'tool_call_id': tool_call_id, **tool_result}})}\n\n"
                    
                    # Add to memory
                    memory.add_message("tool", json.dumps({
                        "name": tool_call.name,
                        "result": tool_result["output"],
                        "success": tool_result["success"],
                    }))
            
            # Max steps reached
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'Reached maximum steps ({request.max_steps})'}})}\n\n"
            
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
    if "model" in updates or "workspace" in updates or "max_steps" in updates or "temperature" in updates:
        agent = ReActAgent(
            model=current_config.model,
            max_steps=current_config.max_steps,
            workspace=Path(current_config.workspace_path),
            temperature=current_config.temperature,
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
    
    # Update config with CLI args
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