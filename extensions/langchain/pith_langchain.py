"""
Pith LangChain Callback Handler — Template.

Intercepts LLM calls to optimize prompts and detect injection attacks.

Usage:
    from pith_langchain import PithCallbackHandler

    pith = PithCallbackHandler(mode="local")
    llm = ChatOpenAI(callbacks=[pith])
"""

from typing import Any

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.messages import BaseMessage

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseCallbackHandler = object  # type: ignore

try:
    from pith.optimizer import optimize_messages
    from pith.injection import check_injection

    PITH_AVAILABLE = True
except ImportError:
    PITH_AVAILABLE = False


class InjectionDetectedError(Exception):
    """Raised when prompt injection is detected in user input."""

    def __init__(self, score: float, patterns: list[str]):
        self.score = score
        self.patterns = patterns
        super().__init__(
            f"Injection detected (score: {score}, patterns: {', '.join(patterns)})"
        )


class PithCallbackHandler(BaseCallbackHandler):
    """LangChain callback that optimizes prompts and checks for injection.

    Args:
        mode: "local" (uses installed pith library) or "cloud" (calls Pith API)
        api_key: Pith Cloud API key (only for cloud mode)
        check_injection: Whether to check for prompt injection (default: True)
        optimize: Whether to optimize prompts (default: True)
        injection_threshold: Score threshold for raising InjectionDetectedError (default: 0.7)
    """

    def __init__(
        self,
        mode: str = "local",
        api_key: str | None = None,
        check_injection_enabled: bool = True,
        optimize: bool = True,
        injection_threshold: float = 0.7,
    ):
        super().__init__()
        self.mode = mode
        self.api_key = api_key
        self.check_injection_enabled = check_injection_enabled
        self.optimize_enabled = optimize
        self.injection_threshold = injection_threshold
        self.stats = {
            "calls": 0,
            "tokens_saved": 0,
            "injections_blocked": 0,
        }

        if mode == "local" and not PITH_AVAILABLE:
            raise ImportError(
                "Pith not installed. Run: pip install pith\n"
                "Or use mode='cloud' with an API key."
            )

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Called before LLM call — optimize and check injection."""
        self.stats["calls"] += 1

        for i, prompt in enumerate(prompts):
            # Injection check
            if self.check_injection_enabled and PITH_AVAILABLE:
                result = check_injection(prompt)
                if result.is_injection and result.score >= self.injection_threshold:
                    self.stats["injections_blocked"] += 1
                    raise InjectionDetectedError(
                        score=result.score,
                        patterns=result.matched_patterns,
                    )

            # Optimization
            if self.optimize_enabled and PITH_AVAILABLE:
                messages = [{"role": "user", "content": prompt}]
                optimized, _ = optimize_messages(messages)
                new_content = optimized[0]["content"]
                saved = len(prompt) - len(new_content)
                if saved > 0:
                    prompts[i] = new_content
                    self.stats["tokens_saved"] += saved

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        """Called before chat model call — optimize message lists."""
        # TODO: Implement chat message optimization
        # This requires converting BaseMessage objects to dicts,
        # running optimize_messages, and converting back.
        pass
