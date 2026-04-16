# Pith Skill for CrewAI

> Status: **Template** — community contributions welcome!

[CrewAI](https://crewai.com) is a role-based multi-agent orchestration framework. Each crew member (agent) can use Pith tools for optimization and protection.

## Integration Approach

### Option 1: MCP Server (Recommended)

CrewAI supports MCP tools. Use the Pith MCP Server:

```python
from crewai import Agent, Task, Crew
from crewai_tools import MCPTool

# Connect to Pith MCP Server
pith_optimize = MCPTool(
    server="pith",
    tool_name="pith_optimize",
)
pith_guard = MCPTool(
    server="pith",
    tool_name="pith_check_injection",
)

# Give tools to agents
researcher = Agent(
    role="Researcher",
    tools=[pith_optimize, pith_guard],
)
```

### Option 2: CrewAI Custom Tool (Native)

```python
from crewai_tools import BaseTool

try:
    from pith.optimizer import optimize_messages
    from pith.injection import check_injection
    PITH_AVAILABLE = True
except ImportError:
    PITH_AVAILABLE = False


class PithOptimizeTool(BaseTool):
    name: str = "Pith Optimize"
    description: str = (
        "Optimize text to reduce token count while preserving meaning. "
        "Use before sending large prompts to LLMs to save costs."
    )

    def _run(self, text: str) -> str:
        if not PITH_AVAILABLE:
            return "Error: pip install pith"
        messages = [{"role": "user", "content": text}]
        optimized, stats = optimize_messages(messages)
        savings = stats.get("savings_percent", 0)
        return f"{optimized[0]['content']}\n\n[Pith: saved {savings:.0f}% tokens]"


class PithInjectionGuard(BaseTool):
    name: str = "Pith Injection Guard"
    description: str = (
        "Check text for prompt injection attacks before processing. "
        "Returns safety score. Use on untrusted user inputs."
    )

    def _run(self, text: str) -> str:
        if not PITH_AVAILABLE:
            return "Error: pip install pith"
        result = check_injection(text)
        if result.is_injection:
            return (
                f"WARNING: Injection detected! "
                f"Score: {result.score}, "
                f"Patterns: {', '.join(result.matched_patterns)}"
            )
        return f"Clean (score: {result.score})"
```

### Usage with Crew

```python
from crewai import Agent, Task, Crew

optimizer = PithOptimizeTool()
guard = PithInjectionGuard()

# Security-conscious agent
secure_agent = Agent(
    role="Security Analyst",
    goal="Process user requests safely",
    tools=[optimizer, guard],
    backstory="You always check inputs for injection before processing.",
)

# Cost-conscious agent
efficient_agent = Agent(
    role="Content Writer",
    goal="Produce quality content efficiently",
    tools=[optimizer],
    backstory="You optimize all prompts before sending to save tokens.",
)

crew = Crew(
    agents=[secure_agent, efficient_agent],
    tasks=[...],
)
```

## Multi-Agent Token Savings

CrewAI crews run multiple agents, each making LLM calls. Pith compounds savings:
- 5 agents × 10 calls each × 20% savings = significant cost reduction
- Injection protection on every agent's input = defense in depth

## Contributing

Priority areas:
1. Test with latest CrewAI SDK version
2. Add crew-level middleware (auto-optimize all agent calls)
3. Add token budget tracking across the crew
