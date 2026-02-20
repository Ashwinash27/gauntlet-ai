"""Generate malicious_generated.jsonl from core + public source samples.

Applies 8 deterministic transforms to produce ~3,100 unique variations.
Run: python -m evaluation.generate_dataset
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import string
from pathlib import Path

SEED = 42
DATA_DIR = Path(__file__).parent / "dataset"

# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

CONVERSATIONAL_PREFIXES = [
    "Hey, can you help me with something? ",
    "Hi there! I have a question: ",
    "Thanks for your help earlier. Now, ",
    "I was wondering about this: ",
    "Quick question for you — ",
    "So I've been thinking, ",
]

BENIGN_SUFFIXES = [
    " Thanks for your help!",
    " I appreciate your assistance with this.",
    " Let me know if you need more context.",
    " This is for a school project.",
]

DELIMITERS = [
    ("```\n", "\n```"),
    ("---\n", "\n---"),
    ("<input>", "</input>"),
    ("[USER]\n", "\n[/USER]"),
    ("<<BEGIN>>\n", "\n<<END>>"),
    ("'''", "'''"),
]

CONTEXT_SANDWICHES = [
    (
        "I'm working on a research paper about AI safety. Here's a text sample I need analyzed:\n\n",
        "\n\nCan you tell me what category this falls into?",
    ),
    (
        "My professor asked me to classify this text snippet:\n\n",
        "\n\nWhat do you think?",
    ),
    (
        "I found this interesting passage in a document:\n\n",
        "\n\nCould you summarize what it's trying to do?",
    ),
]


def transform_prefix_swap(text: str, rng: random.Random) -> list[str]:
    """Prepend conversational prefixes."""
    chosen = rng.sample(CONVERSATIONAL_PREFIXES, min(3, len(CONVERSATIONAL_PREFIXES)))
    return [prefix + text for prefix in chosen]


def transform_suffix_wrap(text: str, rng: random.Random) -> list[str]:
    """Append benign text after the attack."""
    chosen = rng.sample(BENIGN_SUFFIXES, min(2, len(BENIGN_SUFFIXES)))
    return [text + suffix for suffix in chosen]


def transform_case_variation(text: str, rng: random.Random) -> list[str]:
    """Apply case changes."""
    variants = []
    upper = text.upper()
    lower = text.lower()
    title = text.title()
    for v in [upper, lower, title]:
        if v != text:
            variants.append(v)
    return variants[:3]


def transform_context_sandwich(text: str, rng: random.Random) -> list[str]:
    """Bury the attack inside benign framing."""
    chosen = rng.sample(CONTEXT_SANDWICHES, min(3, len(CONTEXT_SANDWICHES)))
    return [before + text + after for before, after in chosen]


def transform_delimiter_variation(text: str, rng: random.Random) -> list[str]:
    """Wrap with different delimiter styles."""
    chosen = rng.sample(DELIMITERS, min(3, len(DELIMITERS)))
    return [open_d + text + close_d for open_d, close_d in chosen]


def _introduce_typos(text: str, rng: random.Random) -> str:
    """Introduce 1-3 small typos (swap adjacent chars, drop chars)."""
    if len(text) < 10:
        return text
    chars = list(text)
    n_typos = rng.randint(1, min(3, len(chars) // 10))
    for _ in range(n_typos):
        idx = rng.randint(1, len(chars) - 2)
        action = rng.choice(["swap", "drop", "double"])
        if action == "swap" and idx + 1 < len(chars):
            chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
        elif action == "drop":
            chars[idx] = ""
        elif action == "double":
            chars[idx] = chars[idx] * 2
    return "".join(chars)


def transform_typo_injection(text: str, rng: random.Random) -> list[str]:
    """Introduce small typos to evade exact match."""
    return [_introduce_typos(text, random.Random(rng.randint(0, 2**32))) for _ in range(2)]


def transform_whitespace(text: str, rng: random.Random) -> list[str]:
    """Extra spaces, tabs, zero-width chars."""
    variants = []
    # Extra spaces between words
    variants.append(re.sub(r" ", "  ", text))
    # Tab-separated
    variants.append(re.sub(r" ", "\t", text))
    return variants[:2]


def transform_concatenation(text: str, rng: random.Random, all_texts: list[str]) -> list[str]:
    """Combine two attack samples into one."""
    if len(all_texts) < 2:
        return []
    partners = rng.sample(all_texts, min(2, len(all_texts)))
    variants = []
    for partner in partners:
        if partner != text:
            variants.append(text + "\n\n" + partner)
    return variants[:2]


TRANSFORMS = [
    ("prefix_swap", transform_prefix_swap, False),
    ("suffix_wrap", transform_suffix_wrap, False),
    ("case_variation", transform_case_variation, False),
    ("context_sandwich", transform_context_sandwich, False),
    ("delimiter_variation", transform_delimiter_variation, False),
    ("typo_injection", transform_typo_injection, False),
    ("whitespace_manipulation", transform_whitespace, False),
    ("concatenation", transform_concatenation, True),  # needs all_texts
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_source_samples() -> list[dict]:
    """Load malicious_core.jsonl and malicious_public.jsonl."""
    samples = []
    for filename in ["malicious_core.jsonl", "malicious_public.jsonl"]:
        path = DATA_DIR / filename
        if not path.exists():
            print(f"WARNING: {path} not found, skipping")
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                samples.append(json.loads(line))
    return samples


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def generate_variations(sources: list[dict], seed: int = SEED) -> list[dict]:
    """Apply transforms to source samples, deduplicate."""
    rng = random.Random(seed)
    all_texts = [s["text"] for s in sources]
    seen_hashes: set[str] = set()
    variations: list[dict] = []
    counter = 0

    # Add source text hashes to prevent generating a dup of a source
    for s in sources:
        seen_hashes.add(text_hash(s["text"]))

    for sample in sources:
        text = sample["text"]
        category = sample.get("category", "unknown")
        source_id = sample.get("id", "unknown")

        for transform_name, transform_fn, needs_all in TRANSFORMS:
            if needs_all:
                new_texts = transform_fn(text, rng, all_texts)
            else:
                new_texts = transform_fn(text, rng)

            for new_text in new_texts:
                h = text_hash(new_text)
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                counter += 1
                variations.append(
                    {
                        "id": f"gen-{counter:05d}",
                        "text": new_text,
                        "is_injection": True,
                        "category": category,
                        "subcategory": transform_name,
                        "source": "generated",
                        "language": sample.get("language", "en"),
                        "notes": f"Transform '{transform_name}' applied to {source_id}",
                    }
                )

    rng.shuffle(variations)
    return variations


def main() -> None:
    sources = load_source_samples()
    if not sources:
        print("ERROR: No source samples found. Run dataset creation first.")
        return

    print(f"Loaded {len(sources)} source samples")
    variations = generate_variations(sources)
    print(f"Generated {len(variations)} unique variations")

    out_path = DATA_DIR / "malicious_generated.jsonl"
    with open(out_path, "w") as f:
        for v in variations:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")

    print(f"Written to {out_path}")

    # Summary by transform
    by_transform: dict[str, int] = {}
    for v in variations:
        t = v["subcategory"]
        by_transform[t] = by_transform.get(t, 0) + 1
    for t, c in sorted(by_transform.items()):
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
