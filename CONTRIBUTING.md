# Contributing to Pith

Thanks for your interest in contributing! Pith is an open-core project — the core proxy, rule-based optimizer, and injection detection are open source.

## Ways to contribute

### Injection patterns
The most impactful contribution: add injection detection patterns for new languages or new attack vectors. See `pith/injection.py` — each pattern is a tuple of (regex, name, score).

### Optimization rules
Add verbose phrase replacements or filler word lists for new languages. See `pith/optimizer.py` — patterns are organized by language.

### Integration examples
Show how Pith works with your favorite framework or tool. Add to `examples/`.

### Bug reports
Open an issue with steps to reproduce. Include your Python version and Pith version.

### Skills & extensions
Build integrations for new platforms (VS Code, Cursor, n8n, etc.). See `examples/` for patterns.

## Development setup

```bash
git clone https://github.com/pithtkn-tech/pith.git
cd pith
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Code style

We use [ruff](https://github.com/astral-sh/ruff) for linting:

```bash
ruff check .
ruff format .
```

## Pull requests

1. Fork the repo
2. Create a branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run linter (`ruff check .`)
6. Open a PR

Keep PRs focused on a single change. Include tests for new patterns.

## What stays closed

These components are proprietary (Pith Cloud):
- Pith Distill compression algorithm
- ML model fine-tuning and training data
- Dashboard and analytics backend
- Billing and authentication systems

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 license.
