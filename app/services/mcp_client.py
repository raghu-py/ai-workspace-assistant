from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings


@dataclass(slots=True)
class MCPServerConfig:
    name: str
    command: list[str]
    cwd: str | None = None
    env: dict[str, str] | None = None


class MCPProtocolError(RuntimeError):
    pass


def load_server_configs() -> list[MCPServerConfig]:
    config_path = Path(settings.mcp_config_path)
    if not config_path.exists():
        return []
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    servers: list[MCPServerConfig] = []
    for item in raw.get("servers", []):
        command = item.get("command")
        if not isinstance(command, list) or not command:
            continue
        servers.append(
            MCPServerConfig(
                name=str(item.get("name", "server")).strip(),
                command=[str(part) for part in command],
                cwd=item.get("cwd"),
                env={str(k): str(v) for k, v in dict(item.get("env", {})).items()},
            )
        )
    return servers


class StdioMCPClient:
    def __init__(self, config: MCPServerConfig):
        self.config = config
        env = os.environ.copy()
        if config.env:
            env.update(config.env)
        self.process = subprocess.Popen(
            config.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=config.cwd,
            env=env,
        )
        self._message_id = 0

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def _next_id(self) -> int:
        self._message_id += 1
        return self._message_id

    def _send(self, payload: dict[str, Any]) -> None:
        if not self.process.stdin:
            raise MCPProtocolError("MCP stdin is unavailable")
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        self.process.stdin.write(header + body)
        self.process.stdin.flush()

    def _read_message(self) -> dict[str, Any]:
        if not self.process.stdout:
            raise MCPProtocolError("MCP stdout is unavailable")
        headers = b""
        while b"\r\n\r\n" not in headers:
            chunk = self.process.stdout.read(1)
            if not chunk:
                stderr = b""
                if self.process.stderr:
                    stderr = self.process.stderr.read() or b""
                raise MCPProtocolError(f"Unexpected end of stream from MCP server: {stderr.decode('utf-8', 'ignore')}")
            headers += chunk
        header_text, _, _ = headers.partition(b"\r\n\r\n")
        content_length = None
        for line in header_text.decode("ascii", "ignore").split("\r\n"):
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
                break
        if content_length is None:
            raise MCPProtocolError("Missing Content-Length header")
        body = self.process.stdout.read(content_length)
        return json.loads(body.decode("utf-8"))

    def _request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        request_id = self._next_id()
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}})
        while True:
            message = self._read_message()
            if message.get("id") == request_id:
                if "error" in message:
                    raise MCPProtocolError(str(message["error"]))
                return message.get("result")

    def initialize(self) -> None:
        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ai-workspace-assistant", "version": "1.0.0"},
            },
        )
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def list_tools(self) -> list[dict[str, Any]]:
        result = self._request("tools/list", {})
        return list(result.get("tools", []))

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        return dict(result)


def with_client(config: MCPServerConfig):
    client = StdioMCPClient(config)
    client.initialize()
    return client
