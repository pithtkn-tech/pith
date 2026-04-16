# Pith for LangChain

> Status: **Template** — community contributions welcome!

LangChain callback handler that optimizes prompts and checks for injection before every LLM call.

## Quick Start

```python
from langchain_openai import ChatOpenAI
from pith_langchain import PithCallbackHandler

# Add Pith as a callback
pith = PithCallbackHandler(mode="local")  # or mode="cloud", api_key="pk_..."

llm = ChatOpenAI(
    model="gpt-4o",
    callbacks=[pith],
)

# Every LLM call now gets optimized + injection-checked
response = llm.invoke("I basically want to essentially understand Python decorators")
# Pith silently optimizes: "Explain Python decorators"
# Savings: ~60% fewer tokens
```

## Features

- **Automatic optimization**: Every prompt is optimized before hitting the LLM
- **Injection detection**: User inputs are checked; flagged messages raise `InjectionDetectedError`
- **Token tracking**: Access savings stats via `pith.stats`
- **Chain-aware**: Works with chains, agents, and retrieval pipelines

## Installation

```bash
pip install pith langchain-openai
```

## Contributing

Priority areas:
1. Implement the callback handler in `pith_langchain.py`
2. Add `on_chain_start` hook for chain-level optimization
3. Add retrieval-aware optimization (don't optimize retrieved context)
4. Package as `pip install pith-langchain`
