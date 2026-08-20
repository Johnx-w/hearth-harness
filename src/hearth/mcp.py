from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Handler = Callable[[dict], str]


@dataclass
class McpHub:
	"""Host-owned MCP tools. Names are mcp__server__tool. Permission uses servers."""

	servers: set[str] = field(default_factory=set)
	schemas: list[dict] = field(default_factory=list)
	handlers: dict[str, Handler] = field(default_factory=dict)

	def connect(
		self,
		server: str,
		*,
		name: str,
		description: str,
		handler: Handler,
		input_schema: dict | None = None,
	) -> str:
		"""Host registers a server tool. Next assemble_tool_pool sees mcp__*."""
		if not server or not name:
			raise ValueError("server and name are required")
		if "__" in server or "__" in name:
			raise ValueError("server and tool names cannot contain __")
		full = f"mcp__{server}__{name}"
		self.servers.add(server)
		self.schemas = [schema for schema in self.schemas if schema.get("name") != full]
		self.schemas.append(
			{
				"name": full,
				"description": description,
				"input_schema": input_schema
				or {
					"type": "object",
					"properties": {},
				},
			}
		)
		self.handlers[full] = handler
		return full


def server_from_tool_name(tool_name: str) -> str | None:
	if not tool_name.startswith("mcp__"):
		return None
	parts = tool_name.split("__")
	if len(parts) != 3 or not parts[1] or not parts[2]:
		return None
	return parts[1]
