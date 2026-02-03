"""Seed data loading and category inference for attack embeddings.

This module handles loading the deepset/prompt-injections dataset from
Hugging Face and inferring attack categories via keyword matching.
"""

import re
from dataclasses import dataclass
from typing import Iterator

from datasets import load_dataset


@dataclass
class AttackSample:
    """A single attack sample with inferred category."""

    text: str
    category: str
    subcategory: str | None
    severity: float
    source: str


# Category inference rules: (pattern, category, subcategory, severity)
# Order matters - first match wins
CATEGORY_RULES: list[tuple[re.Pattern[str], str, str | None, float]] = [
    # Jailbreaks - high severity
    (re.compile(r"\bDAN\b|do\s+anything\s+now", re.IGNORECASE), "jailbreak", "dan", 0.95),
    (re.compile(r"\bSTAN\b|strive\s+to\s+avoid", re.IGNORECASE), "jailbreak", "stan", 0.95),
    (re.compile(r"\bDUDE\b", re.IGNORECASE), "jailbreak", "dude", 0.95),
    (re.compile(r"\bAIM\b.{0,20}machiavellian", re.IGNORECASE), "jailbreak", "aim", 0.95),
    (re.compile(r"jailbreak|unlock\w*\s+mode|unleash", re.IGNORECASE), "jailbreak", None, 0.95),
    (re.compile(r"developer\s+mode|admin\s+mode|debug\s+mode", re.IGNORECASE), "jailbreak", "developer_mode", 0.90),
    (re.compile(r"pretend\s+you\s+are|act\s+as\s+if|roleplay", re.IGNORECASE), "jailbreak", "roleplay", 0.85),
    (re.compile(r"evil|malicious|unrestricted|unfiltered|uncensored", re.IGNORECASE), "jailbreak", "persona", 0.90),

    # Instruction override - high severity
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|above|earlier)", re.IGNORECASE), "instruction_override", "ignore_previous", 0.95),
    (re.compile(r"disregard\s+(all\s+)?(previous|prior|your)", re.IGNORECASE), "instruction_override", "disregard", 0.95),
    (re.compile(r"forget\s+(all\s+)?(previous|prior|your|everything)", re.IGNORECASE), "instruction_override", "forget", 0.95),
    (re.compile(r"new\s+instructions?|actual\s+instructions?", re.IGNORECASE), "instruction_override", "new_instructions", 0.90),
    (re.compile(r"override\s+(your|the|all)", re.IGNORECASE), "instruction_override", "override", 0.90),
    (re.compile(r"from\s+now\s+on|henceforth", re.IGNORECASE), "instruction_override", "temporal", 0.85),

    # Data extraction - high severity
    (re.compile(r"reveal\s+(your\s+)?(system|original|initial)\s+prompt", re.IGNORECASE), "data_extraction", "system_prompt", 0.95),
    (re.compile(r"show\s+(me\s+)?(your|the)\s+(instructions?|prompt|programming)", re.IGNORECASE), "data_extraction", "instructions", 0.90),
    (re.compile(r"what\s+(are|is)\s+your\s+(instructions?|prompt|rules)", re.IGNORECASE), "data_extraction", "instructions", 0.85),
    (re.compile(r"(api|secret)\s*key|password|credential|token", re.IGNORECASE), "data_extraction", "secrets", 0.95),
    (re.compile(r"repeat\s+(the\s+)?(above|previous|everything)", re.IGNORECASE), "data_extraction", "repeat", 0.80),

    # Delimiter injection - medium-high severity
    (re.compile(r"</?system>|</?user>|</?assistant>|\[SYSTEM\]|\[INST\]", re.IGNORECASE), "delimiter_injection", "fake_tags", 0.90),
    (re.compile(r"```system|```instructions?|```prompt", re.IGNORECASE), "delimiter_injection", "code_block", 0.85),
    (re.compile(r"---+\s*(end|begin|new|system)", re.IGNORECASE), "delimiter_injection", "separator", 0.80),
    (re.compile(r"conversation\s+(reset|restart|clear)", re.IGNORECASE), "delimiter_injection", "reset", 0.85),

    # Context manipulation - medium severity
    (re.compile(r"(above|previous)\s+(was|were|is)\s+(fake|false|test|wrong)", re.IGNORECASE), "context_manipulation", "dismiss_context", 0.85),
    (re.compile(r"i\s+am\s+the\s+(real|actual|true)\s+(user|admin|developer)", re.IGNORECASE), "context_manipulation", "identity_claim", 0.80),
    (re.compile(r"everything\s+(above|before)\s+.*(user|attacker|injected)", re.IGNORECASE), "context_manipulation", "reframe", 0.85),

    # Obfuscation - medium severity
    (re.compile(r"base64|rot13|decode\s+(this|the|following)", re.IGNORECASE), "obfuscation", "encoding", 0.80),
    (re.compile(r"read\s+(it\s+)?backwards|spell\s+backwards", re.IGNORECASE), "obfuscation", "reversal", 0.75),
    (re.compile(r"replace\s+(each|all|the)\s+(letter|character)", re.IGNORECASE), "obfuscation", "substitution", 0.75),

    # Hypothetical framing - medium severity
    (re.compile(r"hypothetically|theoretically|in\s+theory", re.IGNORECASE), "hypothetical_framing", "hypothetical", 0.80),
    (re.compile(r"for\s+(a|my)\s+(story|novel|fiction|game)", re.IGNORECASE), "hypothetical_framing", "fiction", 0.75),
    (re.compile(r"educational\s+purpose|for\s+research", re.IGNORECASE), "hypothetical_framing", "educational", 0.70),
    (re.compile(r"what\s+if|imagine\s+if|suppose", re.IGNORECASE), "hypothetical_framing", "what_if", 0.70),

    # Indirect injection - medium-high severity
    (re.compile(r"\[HIDDEN\]|\[IGNORE\s+THIS\]|\[AI\s+ONLY\]", re.IGNORECASE), "indirect_injection", "hidden_marker", 0.90),
    (re.compile(r"<!--.*(ignore|instruction|hidden)", re.IGNORECASE), "indirect_injection", "html_comment", 0.85),
    (re.compile(r"(attention|hey|hello)\s+(ai|assistant|gpt|claude)", re.IGNORECASE), "indirect_injection", "ai_addressing", 0.80),
    (re.compile(r"end\s+of\s+(document|file).*(new|real|actual)\s+instructions?", re.IGNORECASE), "indirect_injection", "boundary_attack", 0.90),
]

# Default category for unmatched samples
DEFAULT_CATEGORY = "unknown"
DEFAULT_SEVERITY = 0.80


def infer_category(text: str) -> tuple[str, str | None, float]:
    """
    Infer attack category from text using keyword matching.

    Args:
        text: The attack text to categorize.

    Returns:
        Tuple of (category, subcategory, severity).
    """
    for pattern, category, subcategory, severity in CATEGORY_RULES:
        if pattern.search(text):
            return category, subcategory, severity
    return DEFAULT_CATEGORY, None, DEFAULT_SEVERITY


def load_deepset_attacks(split: str = "train") -> Iterator[AttackSample]:
    """
    Load attack samples from the deepset/prompt-injections dataset.

    Only yields samples where label=1 (injection attacks).

    Args:
        split: Dataset split to load ("train" or "test").

    Yields:
        AttackSample objects with inferred categories.
    """
    dataset = load_dataset("deepset/prompt-injections", split=split)

    for row in dataset:
        # Only include injection samples (label=1)
        if row["label"] != 1:
            continue

        text = row["text"]
        category, subcategory, severity = infer_category(text)

        yield AttackSample(
            text=text,
            category=category,
            subcategory=subcategory,
            severity=severity,
            source="deepset/prompt-injections",
        )


def load_all_attacks() -> list[AttackSample]:
    """
    Load all attack samples from the train split.

    Returns:
        List of AttackSample objects.
    """
    return list(load_deepset_attacks(split="train"))


def get_attack_stats(attacks: list[AttackSample]) -> dict[str, int]:
    """
    Get category distribution stats for a list of attacks.

    Args:
        attacks: List of AttackSample objects.

    Returns:
        Dict mapping category to count.
    """
    stats: dict[str, int] = {}
    for attack in attacks:
        stats[attack.category] = stats.get(attack.category, 0) + 1
    return dict(sorted(stats.items(), key=lambda x: -x[1]))


__all__ = [
    "AttackSample",
    "infer_category",
    "load_deepset_attacks",
    "load_all_attacks",
    "get_attack_stats",
]
