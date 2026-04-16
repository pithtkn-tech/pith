# Pith for Cursor

> Status: **Template** — community contributions welcome!

Route Cursor's AI requests through Pith for automatic prompt optimization and injection protection.

## How It Works

Cursor uses OpenAI-compatible API endpoints. By pointing Cursor at a local Pith proxy, all AI requests get optimized transparently.

## Setup

### 1. Install and start Pith

```bash
pip install pith
pith serve --port 8000
```

### 2. Configure Cursor

In Cursor Settings → Models → OpenAI API Base:

```
http://localhost:8000/v1
```

Keep your original API key — Pith forwards it to the real provider.

### 3. Verify

Open Cursor's AI chat and send a message. Check Pith logs:

```
[PITH] Optimized: 150 tokens → 120 tokens (20% saved)
[PITH] Injection check: clean (score: 0.02)
```

## What Gets Optimized

- **Chat messages**: Filler removal, verbose compression
- **Code completions**: System prompt deduplication
- **Inline edits**: Context optimization

## Limitations

- Cursor's built-in models (cursor-small, cursor-large) use internal routing and can't be proxied
- OAuth-authenticated models (Claude Pro via Cursor) bypass local proxy — use API key mode
- Streaming is fully supported

## Advanced: Custom Rules

Create `.pith/rules.yaml` in your project root:

```yaml
# Project-specific optimization rules
preserve_patterns:
  - "TODO:"
  - "FIXME:"
  - "HACK:"

injection_whitelist:
  - "You are a coding assistant"  # Common Cursor system prompt
```

## Contributing

Priority areas:
1. Cursor extension API integration (when available)
2. Auto-configuration script
3. Token savings dashboard overlay
