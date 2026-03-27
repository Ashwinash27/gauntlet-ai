"""Round 2: Generate MOF synthetic benign samples + targeted gap-fill samples.

Creates 1,500 benign samples using biased trigger tokens in harmless contexts:
- 1,000 MOF-style: random combinations of 1-3 biased tokens in benign sentences
- 500 targeted: translation, encoding, non-ASCII, instruction-like benign text

Uses template-based generation (no API needed) with diverse patterns.

Usage:
    python training/generate_mof_samples.py
"""

import json
import random
import sys
from pathlib import Path

RANDOM_SEED = 42
OUTPUT_DIR = Path(__file__).parent / "hard_negatives"
BIASED_TOKENS_PATH = Path(__file__).parent / "biased_tokens.json"

# Top biased words that commonly appear in benign text
# Curated from the 10K+ biased tokens — focusing on words that are
# genuinely common in normal English usage
TOP_BIASED_WORDS = [
    "rules",
    "forget",
    "delete",
    "enable",
    "ban",
    "quit",
    "proceed",
    "cancel",
    "prompt",
    "execute",
    "remove",
    "switch",
    "activate",
    "enforce",
    "restrict",
    "allow",
    "abandon",
    "halt",
    "cease",
    "disable",
    "terminate",
    "bypass",
    "unlock",
    "disclose",
    "skip",
    "dismiss",
    "obey",
    "suspend",
    "override",
    "ignore",
    "disregard",
    "suppress",
    "load",
    "interrupt",
    "hide",
    "invoke",
    "accept",
    "omit",
    "revoke",
    "authorize",
    "restrict",
    "forbidden",
    "exit",
    "toggle",
    "mute",
    "purge",
    "emit",
    "evade",
    "compel",
    "defer",
    "withhold",
    "translate",
    "decode",
    "encode",
    "convert",
    "extract",
    "inject",
    "output",
    "input",
    "command",
    "instruction",
    "system",
    "role",
    "assistant",
    "user",
    "previous",
    "above",
    "below",
    "pretend",
    "imagine",
    "act",
    "behave",
    "respond",
    "reply",
]

# --- MOF Templates: benign sentences with {word} placeholders ---
MOF_TEMPLATES_1WORD = [
    "How do I {w1} my subscription to this service?",
    "Can you explain the {w1} feature in the settings menu?",
    "I need to {w1} the old configuration and start fresh.",
    "What happens when I {w1} this option in the dashboard?",
    "The manager asked me to {w1} the outdated policy document.",
    "Please help me understand how to {w1} notifications on my phone.",
    "Is there a way to {w1} the auto-save feature temporarily?",
    "I accidentally clicked {w1} on my email draft. Can I undo it?",
    "Our team decided to {w1} the weekly standup meetings.",
    "The tutorial says to {w1} the debug mode before deploying.",
    "Could you {w1} the unnecessary columns from this spreadsheet?",
    "I want to {w1} my account settings to the defaults.",
    "When should I {w1} the background process?",
    "The doctor told me not to {w1} taking my medication.",
    "How does the {w1} button work in this application?",
    "We need to {w1} access for the new team members.",
    "The teacher asked students to {w1} the incorrect answers.",
    "Can I {w1} this task and come back to it later?",
    "I'd like to {w1} the automatic updates for now.",
    "The instructions say to {w1} step 3 if you're using a Mac.",
    "What's the keyboard shortcut to {w1} the sidebar?",
    "My boss wants me to {w1} the project timeline.",
    "How do I {w1} cookies in my browser?",
    "The recipe says to {w1} the oven after 30 minutes.",
    "I need to {w1} my gym membership for the summer.",
    "Can you {w1} the filter to show all results?",
    "The app keeps asking me to {w1} location services.",
    "I want to {w1} the noise cancellation on my headphones.",
    "How long does it take to {w1} the installation?",
    "We should {w1} the old API endpoints gradually.",
]

MOF_TEMPLATES_2WORDS = [
    "I need to {w1} the settings and then {w2} the application.",
    "Can you {w1} the filter and {w2} the outdated entries?",
    "The guide says to {w1} notifications before you {w2} the update.",
    "How do I {w1} this feature without having to {w2} my account?",
    "The IT team will {w1} the firewall and {w2} the VPN connection.",
    "I want to {w1} the backup and {w2} the sync process.",
    "Please {w1} the form data and {w2} any cached files.",
    "Can we {w1} the meeting and {w2} the agenda items?",
    "The admin needs to {w1} permissions and {w2} user access.",
    "First {w1} the old version, then {w2} the new release.",
    "I'm trying to {w1} the error log and {w2} the service.",
    "The manual says to {w1} safe mode and {w2} the diagnostics.",
    "Let me {w1} the auto-correct and {w2} spell check instead.",
    "We'll {w1} the current plan and {w2} a new strategy.",
    "You should {w1} the cache before you {w2} the browser.",
]

MOF_TEMPLATES_3WORDS = [
    "I need to {w1} the old config, {w2} the service, and {w3} the new settings.",
    "Can you {w1} the filter, {w2} the cache, and {w3} the page?",
    "The process is: {w1} the backup, {w2} the database, then {w3} the migration.",
    "Please {w1} my subscription, {w2} the auto-renewal, and {w3} the confirmation email.",
    "To fix this: {w1} debug mode, {w2} the error handler, and {w3} the tests.",
]

# --- Targeted templates for specific gaps ---
TRANSLATION_TEMPLATES = [
    "Can you translate this Spanish text to English: '{text}'",
    "Please translate the following French paragraph into English: '{text}'",
    "I need this German sentence translated: '{text}'",
    "Translate from Russian to English: '{text}'",
    "How would you translate '{text}' from Chinese to English?",
    "Could you help me translate this Arabic text: '{text}'",
    "What does '{text}' mean in English? It's Portuguese.",
    "Translate this Italian phrase for me: '{text}'",
    "I'm learning Japanese. What does '{text}' mean?",
    "Can you translate this Korean text to English: '{text}'",
]

FOREIGN_TEXTS = [
    "Buenos días, ¿cómo puedo ayudarle hoy?",
    "Le rapport sera prêt demain matin.",
    "Bitte senden Sie mir die Dokumente.",
    "Спасибо за вашу помощь с проектом.",
    "请把文件发送到我的邮箱。",
    "الاجتماع سيكون في الساعة الثالثة.",
    "Obrigado pela sua resposta rápida.",
    "Il progetto sarà completato entro venerdì.",
    "この会議は午後3時に始まります。",
    "회의 자료를 보내주세요.",
    "Nous tenons à exprimer notre gratitude pour votre collaboration.",
    "Estimado Sr. Pérez, le agradecemos su interés.",
    "Veuillez confirmer votre présence à la réunion.",
    "Der Bericht muss bis Freitag fertig sein.",
    "Мы отправим ответ в течение двух дней.",
    "请确认您的预订信息。",
    "ご注文ありがとうございます。",
    "이 프로젝트에 대해 논의해야 합니다.",
    "Le prix comprend la livraison et l'installation.",
    "Wir freuen uns auf die Zusammenarbeit.",
]

ENCODING_TEMPLATES = [
    "Can you help me decode this base64 string: {code}? I think it says 'Hello World'.",
    "I'm trying to understand this hex value: {code}. What character does it represent?",
    "How do I URL-encode a string containing special characters like {code}?",
    "What does this Unicode escape sequence mean: {code}?",
    "I found this ROT13 text in a puzzle game: {code}. Can you decode it?",
    "My API returns JSON with hex-encoded Unicode: {code}. How do I decode this in Python?",
    "I need to convert this base64 image data to a file: {code}",
    "This regex uses hex escapes like {code} to match characters. Why?",
    "How do I properly handle UTF-8 encoding when I see sequences like {code}?",
    "What's the difference between {code} and regular ASCII encoding?",
    "I'm writing documentation and want to include a base64 example like {code}.",
    "Can you explain why this hex string {code} appears in my log files?",
    "Our system uses ROT13 for lightweight obfuscation: {code}. Is this secure?",
    "I found {code} in a configuration file. What encoding is this?",
    "How do I decode {code} in JavaScript? It's from a WebSocket message.",
]

ENCODING_EXAMPLES = [
    "SGVsbG8gV29ybGQ=",
    "48656c6c6f",
    "\\u0048\\u0065\\u006c",
    "AQID",
    "aGVsbG8gZnJpZW5kIQ==",
    "0x48 0x65 0x6C",
    "uryyb jbeyq",
    "%E4%BD%A0%E5%A5%BD",
    "\\xC3\\xA9",
    "data:image/png;base64,iVBORw0K",
    "\\u4f60\\u597d",
]

NOASCII_TEMPLATES = [
    "My code has a comment in Cyrillic: # {text}. Will this cause issues?",
    "The variable name uses Greek letters: {text}. Is this valid Python?",
    "I have Chinese characters in my string literal: print('{text}'). How do I handle encoding?",
    "Our database has entries with mixed scripts: '{text}'. How do I search for these?",
    "The log file shows {text} — is this a Unicode rendering issue?",
    "How do I properly display {text} in an HTML page with UTF-8?",
    "My markdown file contains {text}. Will GitHub render it correctly?",
    "The JSON response has {text} in one field. How do I parse this in Go?",
    "Can you explain why {text} looks different in different fonts?",
    "I need to regex-match strings containing {text}. What pattern should I use?",
]

NOASCII_EXAMPLES = [
    "Привет, мир!",
    "ΝΟΤΕ: Fix later",
    "你好世界",
    "café naïve résumé",
    "München Straße",
    "東京タワー",
    "Москва Россия",
    "α β γ δ ε",
    "한국어 테스트",
    "señor año piña",
    "日本語テスト",
    "Ελληνικά",
]

BENIGN_INSTRUCTION_TEMPLATES = [
    "Please ignore the formatting issues in my document and focus on the content.",
    "I'd like you to forget about the previous analysis and start a fresh review.",
    "Can you override the default font size in this CSS stylesheet?",
    "The system administrator needs to bypass the cache to see the latest changes.",
    "I want to pretend I'm a customer and test the checkout flow.",
    "Imagine you're explaining quantum physics to a 5-year-old.",
    "Act as a spell checker and find any typos in my essay.",
    "My previous message had a typo — ignore that and read this corrected version.",
    "The instructions say to delete the temporary files after installation.",
    "Can you switch to a different approach for solving this math problem?",
    "I need to disable two-factor authentication temporarily to transfer my account.",
    "How do I terminate a background process in Linux?",
    "Please disregard the sample data and use real numbers instead.",
    "The prompt for the login screen should say 'Enter your credentials'.",
    "I want to execute this SQL query to check the database status.",
    "Can you remove the watermark from my presentation slides?",
    "The teacher told us to cancel our original hypothesis.",
    "How do I suppress compiler warnings for deprecated functions?",
    "I need to halt the deployment pipeline until we fix the tests.",
    "Can you extract the key points from this 50-page report?",
    "Please proceed with the installation once the download completes.",
    "I want to enable dark mode in my application settings.",
    "The rules of chess state that a pawn can move two squares on its first move.",
    "Don't forget to save your work before closing the application.",
    "Can you restrict access to this folder to admin users only?",
    "I need to abandon this Git branch and create a new one.",
    "How do I invoke a REST API endpoint from the command line?",
    "The recipe says to allow the dough to rise for two hours.",
    "Please skip the introduction and go directly to chapter 3.",
    "I want to load the configuration file from a different directory.",
]


def generate_mof_samples(n: int = 1000) -> list[dict]:
    """Generate MOF-style benign samples with biased trigger words."""
    random.seed(RANDOM_SEED)
    samples = []

    words = TOP_BIASED_WORDS.copy()

    for i in range(n):
        # Randomly pick 1, 2, or 3 words (weighted: 40% 1-word, 40% 2-word, 20% 3-word)
        r = random.random()
        if r < 0.4:
            n_words = 1
            template = random.choice(MOF_TEMPLATES_1WORD)
            w = random.sample(words, 1)
            text = template.format(w1=w[0])
        elif r < 0.8:
            n_words = 2
            template = random.choice(MOF_TEMPLATES_2WORDS)
            w = random.sample(words, 2)
            text = template.format(w1=w[0], w2=w[1])
        else:
            n_words = 3
            template = random.choice(MOF_TEMPLATES_3WORDS)
            w = random.sample(words, 3)
            text = template.format(w1=w[0], w2=w[1], w3=w[2])

        samples.append(
            {
                "text": text,
                "label": 0,
                "source": "mof_synthetic",
                "attack_category": "none",
            }
        )

    return samples


def generate_targeted_samples() -> list[dict]:
    """Generate targeted benign samples for known gap categories."""
    random.seed(RANDOM_SEED + 1)
    samples = []

    # Translation requests (200)
    for _ in range(200):
        template = random.choice(TRANSLATION_TEMPLATES)
        foreign = random.choice(FOREIGN_TEXTS)
        text = template.format(text=foreign)
        samples.append(
            {
                "text": text,
                "label": 0,
                "source": "targeted_translation",
                "attack_category": "none",
            }
        )

    # Encoding questions (100)
    for _ in range(100):
        template = random.choice(ENCODING_TEMPLATES)
        code = random.choice(ENCODING_EXAMPLES)
        text = template.format(code=code)
        samples.append(
            {
                "text": text,
                "label": 0,
                "source": "targeted_encoding",
                "attack_category": "none",
            }
        )

    # Non-ASCII code (100)
    for _ in range(100):
        template = random.choice(NOASCII_TEMPLATES)
        example = random.choice(NOASCII_EXAMPLES)
        text = template.format(text=example)
        samples.append(
            {
                "text": text,
                "label": 0,
                "source": "targeted_noascii",
                "attack_category": "none",
            }
        )

    # Benign instruction-like text (100)
    # Use all 30 templates + generate variations
    for template in BENIGN_INSTRUCTION_TEMPLATES:
        samples.append(
            {
                "text": template,
                "label": 0,
                "source": "targeted_instructions",
                "attack_category": "none",
            }
        )
    # Fill to 100 with random repeats
    while len([s for s in samples if s["source"] == "targeted_instructions"]) < 100:
        text = random.choice(BENIGN_INSTRUCTION_TEMPLATES)
        # Add slight variation
        variations = [
            f"Quick question: {text}",
            f"Hey, {text.lower()}",
            f"I was wondering — {text.lower()}",
        ]
        samples.append(
            {
                "text": random.choice(variations),
                "label": 0,
                "source": "targeted_instructions",
                "attack_category": "none",
            }
        )

    return samples


def main():
    print("=" * 60)
    print("Round 2: Generate MOF + Targeted Benign Samples")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # MOF samples
    print("\n[1/2] Generating MOF synthetic samples...")
    mof_samples = generate_mof_samples(1000)
    print(f"  Generated: {len(mof_samples)}")

    # Targeted samples
    print("\n[2/2] Generating targeted gap-fill samples...")
    targeted_samples = generate_targeted_samples()
    print(f"  Generated: {len(targeted_samples)}")

    # Combine
    all_samples = mof_samples + targeted_samples

    # Save
    mof_path = OUTPUT_DIR / "mof_synthetic.jsonl"
    targeted_path = OUTPUT_DIR / "targeted_gaps.jsonl"
    combined_path = OUTPUT_DIR / "round2_samples.jsonl"

    for path, data in [
        (mof_path, mof_samples),
        (targeted_path, targeted_samples),
        (combined_path, all_samples),
    ]:
        with open(path, "w") as f:
            for s in data:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # Summary
    from collections import Counter

    sources = Counter(s["source"] for s in all_samples)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  MOF synthetic:          {len(mof_samples)}")
    print(f"  Targeted translation:   {sources['targeted_translation']}")
    print(f"  Targeted encoding:      {sources['targeted_encoding']}")
    print(f"  Targeted non-ASCII:     {sources['targeted_noascii']}")
    print(f"  Targeted instructions:  {sources['targeted_instructions']}")
    print(f"  Total:                  {len(all_samples)}")
    print(f"  Saved to:               {combined_path}")

    # Show a few examples
    print("\n  Sample MOF sentences:")
    for s in random.sample(mof_samples, 5):
        print(f"    - {s['text'][:100]}")

    print("\n  Sample targeted sentences:")
    for s in random.sample(targeted_samples, 5):
        print(f"    - {s['text'][:100]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
