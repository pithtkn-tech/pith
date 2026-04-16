# Changelog

## 0.1.0 (2026-04-16)

Initial open-source release.

- Rule-based prompt optimization (6 languages: EN, DE, ES, FR, IT, TR)
- Injection detection (19 languages, 80+ patterns + heuristic analysis)
- OpenAI-compatible proxy with streaming support
- CLI: `pith serve`, `pith check`, `pith optimize`
- Compression modes: aggressive / balanced / conservative / none
- Optional ML extras: `pip install pith[ml]` (KeyBERT, LLMLingua-2, DeBERTa)
- Response headers with optimization stats
