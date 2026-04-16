# Pith Skill for OpenClaw

> Status: **Template** — community contributions welcome!

[OpenClaw](https://openclaw.dev) is an orchestration-focused agent runtime (Node.js) with a built-in skill marketplace.

## Integration Approach

OpenClaw agents can use Pith in two ways:

### Option 1: MCP Server (Recommended)

OpenClaw supports MCP natively. Use the Pith MCP Server for zero-code integration:

```json
// openclaw.config.json
{
  "mcp_servers": {
    "pith": {
      "command": "python",
      "args": ["path/to/extensions/mcp-server/server.py"]
    }
  }
}
```

Your agent automatically gets `pith_optimize`, `pith_check_injection`, and `pith_count_tokens` tools.

### Option 2: OpenClaw Skill (Native)

For deeper integration with OpenClaw's skill lifecycle:

```typescript
// pith-skill/index.ts
import { Skill, SkillContext } from '@openclaw/sdk';

export default class PithSkill extends Skill {
  name = 'pith';
  description = 'Prompt optimization & injection protection';

  tools = [
    {
      name: 'optimize_prompt',
      description: 'Optimize text to reduce tokens while preserving meaning',
      parameters: {
        text: { type: 'string', required: true },
      },
      handler: async (params: { text: string }, ctx: SkillContext) => {
        // Option A: Call local pith proxy
        const res = await fetch(`http://localhost:8000/v1/optimize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: params.text }),
        });
        return res.json();
      },
    },
    {
      name: 'check_injection',
      description: 'Check text for prompt injection attacks (19 languages)',
      parameters: {
        text: { type: 'string', required: true },
      },
      handler: async (params: { text: string }, ctx: SkillContext) => {
        const res = await fetch(`http://localhost:8000/v1/check`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: params.text }),
        });
        return res.json();
      },
    },
  ];
}
```

## Publishing to OpenClaw Marketplace

```bash
cd skills/openclaw
npm publish --registry https://registry.openclaw.dev
```

## Contributing

Priority areas:
1. Implement the skill with working OpenClaw SDK integration
2. Add pre/post hooks for automatic optimization on every LLM call
3. Add OpenClaw memory integration (optimize before storing to memory)
4. Publish to OpenClaw marketplace
