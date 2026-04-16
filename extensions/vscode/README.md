# Pith for VS Code

> Status: **Template** — community contributions welcome!

Optimize LLM prompts and detect injection attacks directly in VS Code.

## Planned Features

- **Prompt optimization**: Select text → "Optimize with Pith" command
- **Injection detection**: Real-time highlighting of injection patterns in prompt files
- **Token counter**: Status bar showing token count + estimated savings
- **Proxy toggle**: Start/stop local Pith proxy from VS Code

## Architecture

```
VS Code Extension
  ├── commands/
  │   ├── optimize.ts      # "Optimize Selection" command
  │   ├── check.ts         # "Check for Injection" command
  │   └── proxy.ts         # Start/stop local proxy
  ├── providers/
  │   ├── diagnostic.ts    # Injection pattern diagnostics
  │   ├── codelens.ts      # Inline token counts
  │   └── statusbar.ts     # Token savings indicator
  └── extension.ts         # Entry point
```

## Getting Started

```bash
# Prerequisites
npm install -g yo generator-code

# Scaffold
cd extensions/vscode
npm install
npm run compile

# Test
code --extensionDevelopmentPath=.
```

## Configuration

```json
// .vscode/settings.json
{
  "pith.mode": "local",           // "local" | "cloud"
  "pith.localPort": 8000,
  "pith.apiKey": "",              // For cloud mode
  "pith.autoOptimize": false,
  "pith.showTokenCount": true
}
```

## Contributing

This is a template — the core structure is defined but implementation is needed.
See the [main CONTRIBUTING guide](../../CONTRIBUTING.md).

Priority areas:
1. Basic "Optimize Selection" command using local `pith` CLI
2. Injection pattern diagnostics provider
3. Status bar token counter
