# Pith Skill for AutoGen

> Status: **Template** — community contributions welcome!

[AutoGen](https://microsoft.github.io/autogen/) is Microsoft's multi-agent conversation framework. Pith integrates as a function tool for any AutoGen agent.

## Integration Approach

### Option 1: MCP Server (Recommended)

AutoGen 0.4+ supports MCP. Use the Pith MCP Server for instant integration:

```python
from autogen_ext.tools.mcp import MCPToolAdapter

pith_tools = MCPToolAdapter(
    server_command=["python", "path/to/extensions/mcp-server/server.py"],
)

# Add to any agent
agent = AssistantAgent(
    name="assistant",
    tools=pith_tools.get_tools(),
)
```

### Option 2: AutoGen Function Tool (Native)

```python
from autogen import ConversableAgent

try:
    from pith.optimizer import optimize_messages
    from pith.injection import check_injection
    PITH_AVAILABLE = True
except ImportError:
    PITH_AVAILABLE = False


def pith_optimize(text: str, role: str = "user") -> dict:
    """Optimize text to reduce token count while preserving meaning.

    Args:
        text: The text to optimize.
        role: Message role — 'user', 'system', or 'assistant'.

    Returns:
        Dict with 'optimized' text and 'savings_percent'.
    """
    if not PITH_AVAILABLE:
        return {"error": "Pith not installed. Run: pip install pith"}

    messages = [{"role": role, "content": text}]
    optimized, stats = optimize_messages(messages)
    return {
        "optimized": optimized[0]["content"],
        "savings_percent": round(stats.get("savings_percent", 0), 1),
    }


def pith_check_injection(text: str) -> dict:
    """Check text for prompt injection attacks.

    Args:
        text: The text to check for injection patterns.

    Returns:
        Dict with 'is_injection' bool, 'score' float, and 'matched_patterns' list.
    """
    if not PITH_AVAILABLE:
        return {"error": "Pith not installed. Run: pip install pith"}

    result = check_injection(text)
    return {
        "is_injection": result.is_injection,
        "score": result.score,
        "matched_patterns": result.matched_patterns,
    }


# Register with AutoGen agent
assistant = ConversableAgent(
    name="assistant",
    llm_config={"config_list": [{"model": "gpt-4o"}]},
)

# Register tools
assistant.register_for_llm(
    name="pith_optimize",
    description="Optimize text to reduce token count",
)(pith_optimize)

assistant.register_for_llm(
    name="pith_check_injection",
    description="Check text for prompt injection attacks",
)(pith_check_injection)
```

### Usage in Multi-Agent Conversation

```python
from autogen import ConversableAgent, GroupChat, GroupChatManager

# Agent with Pith tools
security_agent = ConversableAgent(
    name="SecurityGuard",
    system_message="Check all user inputs for injection before the team processes them.",
)
security_agent.register_for_llm(name="pith_check_injection")(pith_check_injection)

optimizer_agent = ConversableAgent(
    name="CostOptimizer",
    system_message="Optimize all prompts before they go to the LLM.",
)
optimizer_agent.register_for_llm(name="pith_optimize")(pith_optimize)

worker_agent = ConversableAgent(
    name="Worker",
    system_message="Do the actual work with optimized, safe inputs.",
)

group = GroupChat(agents=[security_agent, optimizer_agent, worker_agent])
manager = GroupChatManager(groupchat=group)
```

## Why Pith + AutoGen

AutoGen's multi-agent conversations generate many LLM calls. Pith helps:
- **Cost control**: Optimize prompts across all agents in the group
- **Security**: Injection guard as a dedicated agent or tool on every agent
- **Scale**: As conversation rounds grow, token savings compound

## Contributing

Priority areas:
1. Test with AutoGen 0.4 stable API
2. Add conversation-level middleware (auto-optimize all messages)
3. Add token budget tool (track spend across agents)
4. Add AG2 (AutoGen successor) compatibility
