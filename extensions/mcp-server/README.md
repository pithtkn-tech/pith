# Pith MCP Server

> Status: **Template** — community contributions welcome!

A [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes Pith optimization and injection detection as MCP tools.

## Why MCP?

MCP is the standard protocol for connecting AI agents to tools. With a Pith MCP server, any MCP-compatible agent (Claude, OpenClaw, Hermes, etc.) can:

- **Optimize prompts** before sending to LLMs
- **Check text for injection attacks** before processing user input
- **Get token estimates** for cost planning

## Tools Exposed

| Tool | Description |
|------|-------------|
| `pith_optimize` | Optimize text, returns optimized version + savings |
| `pith_check_injection` | Check text for injection patterns, returns score + matches |
| `pith_count_tokens` | Count tokens for a given model |
| `pith_health` | Check if Pith proxy is running |

## Quick Start

```bash
# Install dependencies
pip install pith mcp

# Run the MCP server
python server.py

# Or use with Claude Desktop — add to claude_desktop_config.json:
{
  "mcpServers": {
    "pith": {
      "command": "python",
      "args": ["path/to/extensions/mcp-server/server.py"]
    }
  }
}
```

## Contributing

This is a template with a working skeleton. Priority improvements:

1. Add streaming support for large text optimization
2. Add `pith_optimize_messages` tool for full conversation optimization
3. Add configuration resource for compression mode selection
4. Package as `pip install pith-mcp`
