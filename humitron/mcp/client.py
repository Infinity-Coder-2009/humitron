#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Client for Humitron.

Allows Humitron to connect to MCP servers and use their tools dynamically.
Based on the MCP specification and mcp-agent patterns.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path

import httpx
import websockets
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MCPTool(BaseModel):
    """Represents a tool provided by an MCP server."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPResource(BaseModel):
    """Represents a resource provided by an MCP server."""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class MCPPrompt(BaseModel):
    """Represents a prompt template from an MCP server."""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = Field(default_factory=list)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    name: str
    transport: str = "stdio"  # "stdio", "sse", "websocket"
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None  # For SSE/WebSocket transports
    headers: Dict[str, str] = field(default_factory=dict)


class MCPClient:
    """
    Client for communicating with MCP servers.
    
    Supports stdio, SSE, and WebSocket transports.
    Discovers tools, resources, and prompts from connected servers.
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.connections: Dict[str, Any] = {}
        self.tools: Dict[str, MCPTool] = {}  # namespaced: "server.tool"
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, MCPPrompt] = {}
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
    
    def add_server(self, config: MCPServerConfig) -> None:
        """Add an MCP server configuration."""
        self.servers[config.name] = config
        logger.info(f"Added MCP server: {config.name} ({config.transport})")
    
    async def connect_server(self, server_name: str) -> bool:
        """Connect to a specific MCP server."""
        config = self.servers.get(server_name)
        if not config:
            logger.error(f"Server not found: {server_name}")
            return False
        
        try:
            if config.transport == "stdio":
                await self._connect_stdio(config)
            elif config.transport == "sse":
                await self._connect_sse(config)
            elif config.transport == "websocket":
                await self._connect_websocket(config)
            else:
                logger.error(f"Unknown transport: {config transport: {config.transport}")
                return False
            
            # Initialize and discover capabilities
            await self._initialize_server(server_name)
            await self._discover_capabilities(server_name)
            
            logger.info(f"Connected to MCP server: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}")
            return False
    
    async def _connect_stdio(self, config: MCPServerConfig) -> None:
        """Connect via stdio (subprocess)."""
        if not config.command:
            raise ValueError("stdio transport requires command")
        
        proc = await asyncio.create_subprocess_exec(
            config.command,
            *config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **config.env}
        )
        
        self._processes[config.name] = proc
        self.connections[config.name] = {
            "stdin": proc.stdin,
            "stdout": proc.stdout,
            "type": "stdio"
        }
    
    async def _connect_sse(self, config: MCPServerConfig) -> None:
        """Connect via Server-Sent Events."""
        if not config.url:
            raise ValueError("SSE transport requires URL")
        
        client = httpx.AsyncClient(
            timeout=30.0,
            headers=config.headers
        )
        
        self.connections[config.name] = {
            "client": client,
            "url": config.url,
            "type": "sse"
        }
    
    async def _connect_websocket(self, config: MCPServerConfig) -> None:
        """Connect via WebSocket."""
        if not config.url:
            raise ValueError("WebSocket transport requires URL")
        
        ws = await websockets.connect(config.url, extra_headers=config.headers)
        self.connections[config.name] = {
            "websocket": ws,
            "type": "websocket"
        }
    
    async def _send_request(self, server_name: str, method: str, params: Dict = None) -> Dict:
        """Send a JSON-RPC request to an MCP server."""
        conn = self.connections.get(server_name)
        if not conn:
            raise ConnectionError(f"Not connected to server: {server_name}")
        
        request_id = f"{server_name}-{int(time.time() * 1000)}"
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        if conn["type"] == "stdio":
            return await self._send_stdio(conn, request)
        elif conn["type"] == "sse":
            return await self._send_sse(conn, request)
        elif conn["type"] == "websocket":
            return await self._send_websocket(conn, request)
        
        raise ValueError(f"Unknown connection type: {conn['type']}")
    
    async def _send_stdio(self, conn: Dict, request: Dict) -> Dict:
        """Send request via stdio."""
        stdin = conn["stdin"]
        stdout = conn["stdout"]
        
        message = json.dumps(request) + "\n"
        stdin.write(message.encode())
        await stdin.drain()
        
        # Read response
        line = await stdout.readline()
        return json.loads(line.decode())
    
    async def _send_sse(self, conn: Dict, request: Dict) -> Dict:
        """Send request via SSE (HTTP POST)."""
        client = conn["client"]
        response = await client.post(
            conn["url"],
            json=request,
            headers={"Content-Type": "application/json"}
        )
        return response.json()
    
    async def _send_websocket(self, conn: Dict, request: Dict) -> Dict:
        """Send request via WebSocket."""
        ws = conn["websocket"]
        await ws.send(json.dumps(request))
        response = await ws.recv()
        return json.loads(response)
    
    async def _initialize_server(self, server_name: str) -> None:
        """Initialize MCP server connection."""
        await self._send_request(server_name, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "humitron", "version": "0.1.0"}
        })
    
    async def _discover_capabilities(self, server_name: str) -> None:
        """Discover tools, resources, and prompts from server."""
        # List tools
        tools_response = await self._send_request(server_name, "tools/list")
        for tool_data in tools_response.get("result", {}).get("tools", []):
            tool = MCPTool(**tool_data)
            namespaced_name = f"{server_name}.{tool.name}"
            self.tools[namespaced_name] = tool
        
        # List resources
        resources_response = await self._send_request(server_name, "resources/list")
        for res_data in resources_response.get("result", {}).get("resources", []):
            resource = MCPResource(**res_data)
            namespaced_name = f"{server_name}.{resource.name}"
            self.resources[namespaced_name] = resource
        
        # List prompts
        prompts_response = await self._send_request(server_name, "prompts/list")
        for prompt_data in prompts_response.get("result", {}).get("prompts", []):
            prompt = MCPPrompt(**prompt_data)
            namespaced_name = f"{server_name}.{prompt.name}"
            self.prompts[namespaced_name] = prompt
        
        logger.info(f"Discovered {len(self.tools)} tools, "
                   f"{len(self.resources)} resources, "
                   f"{len(self.prompts)} prompts from {server_name}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on an MCP server.
        
        Args:
            tool_name: Namespaced tool name (e.g., "github.search_repos")
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        # Parse server and tool name
        if "." not in tool_name:
            raise ValueError(f"Tool name must be namespaced: {tool_name}")
        
        server_name, actual_tool = tool_name.split(".", 1)
        
        result = await self._send_request(server_name, "tools/call", {
            "name": actual_tool,
            "arguments": arguments
        })
        
        return result.get("result", {})
    
    async def read_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Read a resource from an MCP server."""
        result = await self._send_request("", "resources/read", {"uri": resource_uri})
        return result.get("result", {})
    
    async def get_prompt(self, prompt_name: str, arguments: Dict = None) -> Dict[str, Any]:
        """Get a prompt template from an MCP server."""
        if "." not in prompt_name:
            raise ValueError(f"Prompt name must be namespaced: {prompt_name}")
        
        server_name, actual_prompt = prompt_name.split(".", 1)
        
        result = await self._send_request(server_name, "prompts/get", {
            "name": actual_prompt,
            "arguments": arguments or {}
        })
        
        return result.get("result", {})
    
    def get_tool_schemas(self) -> List[Dict]:
        """Get all discovered tools as OpenAI-compatible schemas."""
        schemas = []
        for namespaced_name, tool in self.tools.items():
            server_name, tool_name = namespaced_name.split(".", 1)
            schemas.append({
                "name": namespaced_name,
                "description": f"[{server_name}] {tool.description}",
                "parameters": tool.input_schema
            })
        return schemas
    
    async def disconnect_server(self, server_name: str) -> None:
        """Disconnect from an MCP server."""
        conn = self.connections.pop(server_name, None)
        if conn:
            if conn["type"] == "stdio":
                proc = self._processes.pop(server_name, None)
                if proc:
                    proc.terminate()
                    await proc.wait()
            elif conn["type"] == "sse":
                await conn["client"].aclose()
            elif conn["type"] == "websocket":
                await conn["websocket"].close()
        
        # Remove discovered capabilities
        self.tools = {k: v for k, v in self.tools.items() if not k.startswith(f"{server_name}.")}
        self.resources = {k: v for k, v in self.resources.items() if not k.startswith(f"{server_name}.")}
        self.prompts = {k: v for k, v in self.prompts.items() if not k.startswith(f"{server_name}.")}
        
        logger.info(f"Disconnected from MCP server: {server_name}")
    
    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        for server_name in list(self.connections.keys()):
            await self.disconnect_server(server_name)


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


# ─── Built-in MCP Server Configurations ─────────────────────────────────────


def get_builtin_servers() -> Dict[str, MCPServerConfig]:
    """Get configurations for common MCP servers."""
    return {
        "filesystem": MCPServerConfig(
            name="filesystem",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", str(Path.cwd())]
        ),
        "github": MCPServerConfig(
            name="github",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.environ.get("GITHUB_TOKEN", "")}
        ),
        "sqlite": MCPServerConfig(
            name="sqlite",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-sqlite", "--db-path", "./data.db"]
        ),
        "postgres": MCPServerConfig(
            name="postgres",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres"],
            env={"POSTGRES_CONNECTION_STRING": os.environ.get("POSTGRES_URL", "")}
        ),
        "brave-search": MCPServerConfig(
            name="brave-search",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"],
            env={"BRAVE_API_KEY": os.environ.get("BRAVE_API_KEY", "")}
        ),
        "fetch": MCPServerConfig(
            name="fetch",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-fetch"]
        ),
        "memory": MCPServerConfig(
            name="memory",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"]
        ),
    }