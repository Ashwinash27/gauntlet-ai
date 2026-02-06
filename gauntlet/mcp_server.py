"""MCP server for Gauntlet prompt injection detection.

Provides two tools for Claude Code integration:
- check_prompt: Run detection cascade on text
- scan_file: Read file and check for injections

Start with: gauntlet mcp-serve

Requires: pip install gauntlet-ai[mcp]
"""

from __future__ import annotations

import json
from pathlib import Path


def serve() -> None:
    """Start the MCP server."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError:
        raise ImportError(
            "MCP server requires the mcp package. "
            "Install with: pip install gauntlet-ai[mcp]"
        )

    import asyncio

    from gauntlet import Gauntlet

    server = Server("gauntlet")
    detector = Gauntlet()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="check_prompt",
                description="Check text for prompt injection attacks using Gauntlet's detection cascade.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to check for prompt injection",
                        },
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="scan_file",
                description="Read a file and check its contents for prompt injection attacks.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to scan",
                        },
                    },
                    "required": ["path"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "check_prompt":
            text = arguments.get("text", "")
            result = detector.detect(text)
            return [TextContent(
                type="text",
                text=json.dumps(result.model_dump(), indent=2),
            )]

        elif name == "scan_file":
            filepath = Path(arguments.get("path", "")).resolve()
            cwd = Path.cwd().resolve()

            # Security: only allow files within current working directory
            try:
                filepath.relative_to(cwd)
            except ValueError:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Access denied: path must be within {cwd}"}),
                )]

            # Block hidden files
            if any(part.startswith(".") for part in filepath.parts if part != "."):
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "Access denied: cannot scan hidden files"}),
                )]

            if not filepath.exists():
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"File not found: {filepath}"}),
                )]

            try:
                text = filepath.read_text()
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Failed to read file: {e}"}),
                )]

            result = detector.detect(text)
            output = result.model_dump()
            output["file"] = str(filepath)
            return [TextContent(
                type="text",
                text=json.dumps(output, indent=2),
            )]

        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"}),
        )]

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            init_options = server.create_initialization_options()
            await server.run(read_stream, write_stream, init_options)

    asyncio.run(_run())


if __name__ == "__main__":
    serve()
