# Pith Extensions

Community-contributed integrations that bring Pith optimization and injection protection to your favorite tools.

## Available Extensions

| Extension | Status | Description |
|-----------|--------|-------------|
| [VS Code](./vscode/) | Template | Optimize prompts directly in VS Code |
| [MCP Server](./mcp-server/) | Template | Model Context Protocol server for agent frameworks |
| [Cursor](./cursor/) | Template | Cursor IDE integration |
| [LangChain](./langchain/) | Template | LangChain callback middleware |

## How Extensions Work

All extensions connect to Pith in one of three ways:

1. **Local proxy** — Run `pith serve` locally, extensions route through it
2. **Pith Cloud** — Extensions call `api.pithtoken.ai` directly (Pro features)
3. **Embedded** — Extension imports `pith` as a library (rule-based only)

```
Your Tool → Extension → Pith (local or cloud) → LLM Provider
```

## Building Your Own Extension

1. Pick a tool/framework that uses LLM APIs
2. Intercept the API call (middleware, proxy config, or plugin hook)
3. Route through Pith for optimization + protection
4. See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines

## Community Contributions Welcome

We especially want extensions for:

- **IDEs**: JetBrains, Neovim, Zed, Aider
- **Agent frameworks**: CrewAI, AutoGen, Hermes, OpenClaw
- **Orchestrators**: n8n, Gumloop, Flowise
- **Local LLM**: Ollama, LM Studio, llama.cpp frontends

Open an issue or PR — we'll review and merge quickly.
