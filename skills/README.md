# Pith Skills — Agent Framework Integrations

Pith skills bring prompt optimization and injection protection to agent runtimes and orchestration frameworks.

## Available Skills

| Skill | Framework | Language | Status |
|-------|-----------|----------|--------|
| [OpenClaw](./openclaw/) | OpenClaw agent runtime | Node.js | Template |
| [Hermes](./hermes/) | Hermes self-evolving agents | Python | Template |
| [CrewAI](./crewai/) | CrewAI multi-agent orchestration | Python | Template |
| [AutoGen](./autogen/) | Microsoft AutoGen agents | Python | Template |

## MCP Server — Universal Alternative

Most modern agent frameworks support [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). Instead of framework-specific skills, you can use the **Pith MCP Server** as a universal integration:

```bash
# Install and run
pip install pith mcp
python extensions/mcp-server/server.py
```

The MCP server exposes `pith_optimize`, `pith_check_injection`, `pith_count_tokens` as standard MCP tools — compatible with any MCP-enabled agent.

See [extensions/mcp-server/](../extensions/mcp-server/) for details.

### When to use MCP vs framework-specific skill

| Use MCP Server when... | Use a skill when... |
|------------------------|---------------------|
| Framework supports MCP | Framework has its own skill/plugin system |
| You want one integration for all agents | You need deep framework hooks (lifecycle, memory) |
| Quick setup is priority | You want framework-native UX |

## How Skills Work

All skills follow the same pattern:

```
Agent receives user input
  → Skill: check_injection(input)     # Block attacks
  → Skill: optimize(messages)          # Reduce tokens
  → Agent calls LLM (fewer tokens)
  → Response flows back normally
```

Skills can run in three modes:

1. **Embedded** — Import `pith` as library (rule-based only, zero network)
2. **Local proxy** — Route through `pith serve` on localhost
3. **Pith Cloud** — Call `api.pithtoken.ai` (Pro features: Pith Distill, ML protection)

## Building a New Skill

1. Check if the framework supports MCP — if yes, use [MCP Server](../extensions/mcp-server/) instead
2. Find the framework's tool/plugin registration API
3. Register `optimize` and `check_injection` as tools
4. See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines

We want skills for: **n8n, Flowise, Gumloop, Semantic Kernel, LlamaIndex, Haystack, Dify** — PRs welcome!
