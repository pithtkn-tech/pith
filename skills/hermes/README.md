# Pith Skill for Hermes

> Status: **Template** — community contributions welcome!

[Hermes](https://github.com/hermes-ai/hermes) is a self-evolving agent runtime (Python) that improves its own performance over time.

## Integration Approach

### Option 1: MCP Server (Recommended)

If Hermes supports MCP, use the universal Pith MCP Server:

```python
# hermes_config.py
mcp_servers = {
    "pith": {
        "command": "python",
        "args": ["path/to/extensions/mcp-server/server.py"],
    }
}
```

### Option 2: Hermes Tool (Native)

Register Pith as a Hermes tool for tighter integration:

```python
# pith_tool.py
from hermes import Tool, ToolResult

try:
    from pith.optimizer import optimize_messages
    from pith.injection import check_injection
    PITH_AVAILABLE = True
except ImportError:
    PITH_AVAILABLE = False


class PithOptimizeTool(Tool):
    """Optimize prompts to reduce token count."""

    name = "pith_optimize"
    description = (
        "Optimize text to reduce token count while preserving meaning. "
        "Removes filler words, compresses verbose phrases. 6 languages."
    )

    def run(self, text: str, role: str = "user") -> ToolResult:
        if not PITH_AVAILABLE:
            return ToolResult(error="Pith not installed. Run: pip install pith")

        messages = [{"role": role, "content": text}]
        optimized, stats = optimize_messages(messages)
        return ToolResult(
            output={
                "optimized": optimized[0]["content"],
                "savings_percent": stats.get("savings_percent", 0),
            }
        )


class PithInjectionTool(Tool):
    """Check text for prompt injection attacks."""

    name = "pith_check_injection"
    description = (
        "Check text for prompt injection patterns. "
        "Detects instruction override, role hijacking, prompt extraction "
        "in 19 languages. Returns score 0.0-1.0."
    )

    def run(self, text: str) -> ToolResult:
        if not PITH_AVAILABLE:
            return ToolResult(error="Pith not installed. Run: pip install pith")

        result = check_injection(text)
        return ToolResult(
            output={
                "is_injection": result.is_injection,
                "score": result.score,
                "matched_patterns": result.matched_patterns,
            }
        )
```

### Registration

```python
from hermes import Agent
from pith_tool import PithOptimizeTool, PithInjectionTool

agent = Agent(
    tools=[PithOptimizeTool(), PithInjectionTool()],
)
```

## Hermes Self-Evolution + Pith

Hermes learns from its interactions. Pith can help by:
- Optimizing prompts that Hermes generates for sub-tasks
- Protecting against injection in user inputs before Hermes processes them
- Reducing token costs as Hermes self-evolves (more iterations = more tokens)

## Contributing

Priority areas:
1. Verify Hermes SDK API and adapt tool registration
2. Add automatic optimization in Hermes lifecycle hooks
3. Add injection guardrail as a pre-execution check
