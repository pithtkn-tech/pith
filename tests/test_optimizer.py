"""Tests for the Pith optimizer — rule-based prompt optimization."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pith.optimizer import optimize_messages


def test_filler_removal():
    """Filler words like 'basically', 'essentially' should be removed."""
    messages = [{"role": "user", "content": "I basically want to essentially understand Python"}]
    optimized, _ = optimize_messages(messages)
    result = optimized[0]["content"]
    assert "basically" not in result.lower()
    assert "essentially" not in result.lower()


def test_verbose_compression():
    """Verbose phrases should be compressed."""
    messages = [{"role": "user", "content": "In order to understand this, due to the fact that it is complex"}]
    optimized, _ = optimize_messages(messages)
    result = optimized[0]["content"]
    assert "In order to" not in result
    assert "due to the fact that" not in result.lower()


def test_polite_fluff_removal():
    """Polite fluff like 'please', 'I would like you to' should be removed."""
    messages = [{"role": "user", "content": "I would like you to please help me understand Python decorators"}]
    optimized, _ = optimize_messages(messages)
    result = optimized[0]["content"]
    assert "I would like you to" not in result
    assert "please" not in result.lower()


def test_redundant_system_instructions():
    """Redundant system instructions should be stripped."""
    messages = [{"role": "system", "content": "You are a very helpful, friendly, and professional AI assistant. Always be respectful and polite. Explain things clearly."}]
    optimized, _ = optimize_messages(messages)
    result = optimized[0]["content"]
    assert len(result) < len(messages[0]["content"])


def test_system_deduplication():
    """Duplicate system messages should be removed."""
    messages = [
        {"role": "system", "content": "You are a coding assistant."},
        {"role": "system", "content": "You are a coding assistant."},
        {"role": "user", "content": "Hello"},
    ]
    optimized, _ = optimize_messages(messages)
    system_count = sum(1 for m in optimized if m["role"] == "system")
    assert system_count == 1


def test_negative_savings_guard():
    """Optimization should never make content bigger."""
    messages = [{"role": "user", "content": "Hi"}]
    optimized, _ = optimize_messages(messages)
    assert len(optimized[0]["content"]) <= len(messages[0]["content"])


def test_assistant_truncation():
    """Old assistant messages should be truncated."""
    long_response = "x " * 200  # 400 chars
    messages = [
        {"role": "user", "content": "question 1"},
        {"role": "assistant", "content": long_response},
        {"role": "user", "content": "question 2"},
        {"role": "assistant", "content": "answer 2"},
        {"role": "user", "content": "question 3"},
        {"role": "assistant", "content": "answer 3"},
        {"role": "user", "content": "question 4"},
    ]
    optimized, _ = optimize_messages(messages)
    # First assistant message (old) should be truncated
    first_assistant = [m for m in optimized if m["role"] == "assistant"][0]
    assert len(first_assistant["content"]) < len(long_response)


def test_german_optimization():
    """German filler words and verbose phrases should be optimized."""
    messages = [{"role": "user", "content": "Ich möchte, dass du mir bitte erklärst, wie Python eigentlich grundsätzlich funktioniert"}]
    optimized, _ = optimize_messages(messages)
    result = optimized[0]["content"]
    assert len(result) < len(messages[0]["content"])


def test_turkish_optimization():
    """Turkish filler words should be optimized."""
    messages = [{"role": "user", "content": "Aslında temelde Python'un nasıl çalıştığını açıkla"}]
    optimized, _ = optimize_messages(messages)
    result = optimized[0]["content"]
    assert len(result) < len(messages[0]["content"])


def test_empty_messages_skipped():
    """Messages that become empty after optimization should be skipped."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
    ]
    optimized, _ = optimize_messages(messages)
    assert all(m["content"].strip() for m in optimized)


def test_non_string_content_preserved():
    """Messages with non-string content (multimodal) should pass through."""
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "What is this?"}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]}
    ]
    optimized, _ = optimize_messages(messages)
    assert optimized[0]["content"] == messages[0]["content"]
