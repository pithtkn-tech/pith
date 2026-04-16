"""
Pith MCP Server — Model Context Protocol integration.

Exposes Pith optimization and injection detection as MCP tools
for use with Claude Desktop, OpenClaw, and other MCP-compatible agents.

Usage:
    python server.py

Or add to Claude Desktop config:
    {
        "mcpServers": {
            "pith": {
                "command": "python",
                "args": ["path/to/server.py"]
            }
        }
    }
"""

import json
import sys

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    from pith.optimizer import optimize_messages
    from pith.injection import check_injection
    from pith.counter import count_tokens

    PITH_AVAILABLE = True
except ImportError:
    PITH_AVAILABLE = False

# --- Server setup ---

server = Server("pith")


@server.list_tools()
async def list_tools():
    """List available Pith tools."""
    tools = [
        Tool(
            name="pith_optimize",
            description=(
                "Optimize text to reduce token count while preserving meaning. "
                "Removes filler words, compresses verbose phrases, strips "
                "redundant instructions. Supports 6 languages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to optimize",
                    },
                    "role": {
                        "type": "string",
                        "enum": ["user", "system", "assistant"],
                        "default": "user",
                        "description": "Message role (affects optimization strategy)",
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="pith_check_injection",
            description=(
                "Check text for prompt injection attacks. "
                "Detects instruction override, role hijacking, prompt extraction, "
                "delimiter injection, and privilege escalation in 19 languages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to check for injection patterns",
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="pith_count_tokens",
            description="Count tokens in text for a given model.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to count tokens for",
                    },
                    "model": {
                        "type": "string",
                        "default": "gpt-4o",
                        "description": "Model name for tokenizer selection",
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="pith_health",
            description="Check if Pith is properly installed and available.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls."""

    if name == "pith_health":
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "status": "ok" if PITH_AVAILABLE else "pith not installed",
                        "available": PITH_AVAILABLE,
                        "install": "pip install pith" if not PITH_AVAILABLE else None,
                    }
                ),
            )
        ]

    if not PITH_AVAILABLE:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "Pith not installed. Run: pip install pith",
                    }
                ),
            )
        ]

    if name == "pith_optimize":
        text = arguments["text"]
        role = arguments.get("role", "user")
        messages = [{"role": role, "content": text}]
        optimized, stats = optimize_messages(messages)
        result = {
            "optimized": optimized[0]["content"],
            "original_length": len(text),
            "optimized_length": len(optimized[0]["content"]),
            "savings_percent": round(stats.get("savings_percent", 0), 1),
        }
        return [TextContent(type="text", text=json.dumps(result))]

    elif name == "pith_check_injection":
        text = arguments["text"]
        result = check_injection(text)
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "is_injection": result.is_injection,
                        "score": result.score,
                        "matched_patterns": result.matched_patterns,
                    }
                ),
            )
        ]

    elif name == "pith_count_tokens":
        text = arguments["text"]
        model = arguments.get("model", "gpt-4o")
        tokens = count_tokens(text, model)
        return [
            TextContent(
                type="text",
                text=json.dumps({"tokens": tokens, "model": model}),
            )
        ]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# --- Main ---

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
