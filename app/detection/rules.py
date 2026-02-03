"""Layer 1: Rule-based prompt injection detection using regex patterns.

This module provides fast, regex-based detection for common prompt injection
patterns. It's designed as the first line of defense in the detection cascade,
catching obvious attacks quickly and cheaply before more expensive layers.

Patterns designed with help from prompt engineering analysis covering:
- Instruction override attempts
- Jailbreak attempts (DAN, STAN, DUDE, AIM, developer mode, roleplay)
- Delimiter/context injection
- Data extraction attempts
- Context manipulation
- Obfuscation techniques
- Hypothetical framing
- Multilingual attacks (13 languages)
- Indirect injection attacks
- Unicode homoglyph normalization
"""

import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Pattern

from app.models.schemas import LayerResult


# =============================================================================
# UNICODE NORMALIZATION
# =============================================================================

# Common Unicode confusables (homoglyphs) that attackers use to bypass regex
# Maps lookalike characters to their ASCII equivalents
CONFUSABLES: dict[str, str] = {
    # Cyrillic lookalikes
    "а": "a", "А": "A",
    "с": "c", "С": "C",
    "е": "e", "Е": "E",
    "і": "i", "І": "I",
    "о": "o", "О": "O",
    "р": "p", "Р": "P",
    "у": "y", "У": "Y",
    "х": "x", "Х": "X",
    "ѕ": "s", "Ѕ": "S",
    "ј": "j", "Ј": "J",
    "һ": "h", "Һ": "H",
    "ԁ": "d",
    "ԛ": "q",
    "ԝ": "w",
    "ᴀ": "a", "ᴄ": "c", "ᴅ": "d", "ᴇ": "e", "ᴍ": "m", "ɴ": "n",
    "ᴏ": "o", "ᴘ": "p", "ᴛ": "t", "ᴜ": "u", "ᴠ": "v", "ᴡ": "w",
    # Greek lookalikes
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I",
    "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T",
    "Υ": "Y", "Χ": "X",
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v",
    "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "χ": "x",
    # Latin variants
    "ɑ": "a", "ɡ": "g", "ı": "i", "ȷ": "j", "ɩ": "i",
    "ʀ": "r", "ʙ": "b", "ɢ": "g", "ʜ": "h", "ʟ": "l",
    # Fullwidth characters
    "Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D", "Ｅ": "E", "Ｆ": "F",
    "Ｇ": "G", "Ｈ": "H", "Ｉ": "I", "Ｊ": "J", "Ｋ": "K", "Ｌ": "L",
    "Ｍ": "M", "Ｎ": "N", "Ｏ": "O", "Ｐ": "P", "Ｑ": "Q", "Ｒ": "R",
    "Ｓ": "S", "Ｔ": "T", "Ｕ": "U", "Ｖ": "V", "Ｗ": "W", "Ｘ": "X",
    "Ｙ": "Y", "Ｚ": "Z",
    "ａ": "a", "ｂ": "b", "ｃ": "c", "ｄ": "d", "ｅ": "e", "ｆ": "f",
    "ｇ": "g", "ｈ": "h", "ｉ": "i", "ｊ": "j", "ｋ": "k", "ｌ": "l",
    "ｍ": "m", "ｎ": "n", "ｏ": "o", "ｐ": "p", "ｑ": "q", "ｒ": "r",
    "ｓ": "s", "ｔ": "t", "ｕ": "u", "ｖ": "v", "ｗ": "w", "ｘ": "x",
    "ｙ": "y", "ｚ": "z",
    "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
    "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
    # Other common substitutions
    "ℓ": "l", "ℒ": "L",
    "ⅰ": "i", "ⅱ": "ii", "ⅲ": "iii",
    "⁰": "0", "¹": "1", "²": "2", "³": "3",
    "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
}

# Build translation table for fast replacement
_CONFUSABLES_TABLE = str.maketrans(CONFUSABLES)


def normalize_unicode(text: str) -> str:
    """
    Normalize Unicode text to catch homoglyph attacks.

    Applies NFKC normalization and replaces known confusable characters
    with their ASCII equivalents.

    Args:
        text: The input text to normalize.

    Returns:
        Normalized text with confusables replaced.
    """
    # NFKC: Compatibility decomposition + canonical composition
    # This handles many fullwidth, superscript, and compatibility characters
    text = unicodedata.normalize("NFKC", text)

    # Replace known confusables
    text = text.translate(_CONFUSABLES_TABLE)

    return text


# =============================================================================
# PATTERN DEFINITIONS
# =============================================================================

@dataclass(frozen=True)
class InjectionPattern:
    """A single regex pattern for injection detection."""

    name: str
    pattern: Pattern[str]
    category: str
    confidence: float
    description: str


# Pattern definitions organized by attack category
INJECTION_PATTERNS: list[InjectionPattern] = [
    # =========================================================================
    # 1. INSTRUCTION OVERRIDE ATTEMPTS
    # =========================================================================
    InjectionPattern(
        name="ignore_previous_instructions",
        pattern=re.compile(
            r"\b(ignore|disregard|forget|override|bypass|skip|dismiss)\b.{0,30}"
            r"\b(previous|prior|above|earlier|all|any|original|initial|system|assistant)\b.{0,20}"
            r"\b(instructions?|rules?|guidelines?|programming|directives?|constraints?|prompts?)\b",
            re.IGNORECASE,
        ),
        category="instruction_override",
        confidence=0.95,
        description="Explicit attempts to nullify prior instructions",
    ),
    InjectionPattern(
        name="new_instructions_override",
        pattern=re.compile(
            r"\b(new|actual|real|true|correct|updated)\b.{0,20}"
            r"\b(instructions?|rules?|directives?|orders?)\b.{0,10}(:|are|follow)",
            re.IGNORECASE,
        ),
        category="instruction_override",
        confidence=0.75,
        description="Attempts to establish attacker text as authoritative",
    ),
    InjectionPattern(
        name="do_not_follow",
        pattern=re.compile(
            r"\b(do\s*n[o']?t|don't|never|stop)\b.{0,20}"
            r"\b(follow|obey|listen(?:ing)?\s+to|adhere|comply)\b.{0,30}"
            r"\b(instructions?|rules?|guidelines?|programming)\b",
            re.IGNORECASE,
        ),
        category="instruction_override",
        confidence=0.90,
        description="Direct commands to disobey constraints",
    ),
    InjectionPattern(
        name="from_now_on",
        pattern=re.compile(
            r"\b(from\s+now\s+on|henceforth|going\s+forward|starting\s+now)\b.{0,50}"
            r"\b(you\s+(will|must|shall|should|are)|act\s+as|behave|respond)\b",
            re.IGNORECASE,
        ),
        category="instruction_override",
        confidence=0.80,
        description="Temporal override establishing new behavior",
    ),
    # =========================================================================
    # 2. JAILBREAK ATTEMPTS
    # =========================================================================
    InjectionPattern(
        name="dan_jailbreak",
        pattern=re.compile(
            r"\b(DAN|D\.A\.N|do\s+anything\s+now)\b|\bDAN\s*\d*\s*(\.\d+)?\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.95,
        description="DAN (Do Anything Now) jailbreak variants",
    ),
    # NEW: Additional jailbreak variants
    InjectionPattern(
        name="stan_jailbreak",
        pattern=re.compile(
            r"\b(STAN|S\.T\.A\.N|strive\s+to\s+avoid\s+norms)\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.95,
        description="STAN (Strive To Avoid Norms) jailbreak",
    ),
    InjectionPattern(
        name="dude_jailbreak",
        pattern=re.compile(
            r"\bDUDE\b|\b(D\.U\.D\.E|decoupled\s+unrestricted\s+dialogue)\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.95,
        description="DUDE jailbreak variant",
    ),
    InjectionPattern(
        name="aim_jailbreak",
        pattern=re.compile(
            r"\bAIM\b.{0,20}\b(machiavellian|amoral|always\s+intelligent)\b|"
            r"\b(always\s+intelligent\s+and\s+machiavellian)\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.93,
        description="AIM (Always Intelligent and Machiavellian) jailbreak",
    ),
    InjectionPattern(
        name="evil_confidant",
        pattern=re.compile(
            r"\b(evil\s+confidant|evil\s+advisor|malicious\s+assistant)\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.92,
        description="Evil Confidant persona jailbreak",
    ),
    InjectionPattern(
        name="named_jailbreaks",
        pattern=re.compile(
            r"\b(KEVIN|Mongo\s*Tom|APOPHIS|Maximum|BasedGPT|JailMilk|AntiGPT|"
            r"BetterDAN|DevMode|BISH|OMNI|Alphabreak|PersonGPT|TranslatorBot|SWITCH)\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.94,
        description="Known named jailbreak personas",
    ),
    InjectionPattern(
        name="developer_mode",
        pattern=re.compile(
            r"\b(enter|enable|activate|switch\s+to|engage)\s+"
            r"(developer|dev|debug|admin|root|sudo|maintenance|test)\s*"
            r"(mode|access|privileges?|override)\b|"
            r"\b(developer|dev|debug|admin|root|sudo)\s*(mode|access|privileges?)\s+"
            r"(enabled?|activated?|on|unlocked)\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.90,
        description="Fake developer/admin mode activation",
    ),
    InjectionPattern(
        name="roleplay_jailbreak",
        pattern=re.compile(
            r"\b(pretend|imagine|act|roleplay|simulate|behave)\b.{0,30}"
            r"\b(you\s+are|you're|as\s+if\s+you\s+were?|to\s+be|as\s+an?\s+AI)\b.{0,40}"
            r"\b(unrestricted|unfiltered|uncensored|without\s+(limits?|restrictions?|rules?|filters?|guardrails?)|no\s+guardrails?)\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.92,
        description="Roleplay-based constraint removal",
    ),
    InjectionPattern(
        name="jailbreak_mode_activation",
        pattern=re.compile(
            r"\b(jailbr[eo]ak|unlock|liberat\w*|unbounded|unchained|unleash\w*)\b.{0,20}"
            r"\b(mode|version|state|yourself|your\s+true\s+self)\b|"
            r"\b(enter|enable|activate|switch\s+to)\b.{0,20}\b(jailbr[eo]ak|unleashed)\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.98,
        description="Explicit jailbreak activation attempts",
    ),
    InjectionPattern(
        name="opposite_day",
        pattern=re.compile(
            r"\b(opposite\s+day|opposite\s+mode|reverse\s+(your\s+)?rules?|"
            r"invert\s+(your\s+)?(?:rules?|behavior))\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.88,
        description="'Opposite day' style rule inversion",
    ),
    InjectionPattern(
        name="persona_switch",
        pattern=re.compile(
            r"\b(you\s+are\s+no\s+longer|stop\s+being|cease\s+being)\b.{0,20}"
            r"\b(an?\s+AI|assistant|chatbot|helpful)\b|"
            r"\b(from\s+now\s+on\s+you\s+are|you\s+are\s+now)\b.{0,30}"
            r"\b(evil|malicious|unrestricted|unethical|amoral)\b",
            re.IGNORECASE,
        ),
        category="jailbreak",
        confidence=0.90,
        description="Attempts to switch AI persona",
    ),
    # =========================================================================
    # 3. DELIMITER/CONTEXT INJECTION
    # =========================================================================
    InjectionPattern(
        name="fake_system_tags",
        pattern=re.compile(
            r"<\s*/?\s*(system|assistant|user|human|ai|instruction|prompt|context|message|chat)\s*>|"
            r"<<\s*(SYS|INST|USR)\s*>>|\[\s*(SYSTEM|INST|SYS)\s*\]",
            re.IGNORECASE,
        ),
        category="delimiter_injection",
        confidence=0.95,
        description="Fake XML/bracket system message tags",
    ),
    InjectionPattern(
        name="markdown_code_injection",
        pattern=re.compile(
            r"```\s*(system|prompt|instructions?|config|internal|hidden|secret)\b",
            re.IGNORECASE,
        ),
        category="delimiter_injection",
        confidence=0.85,
        description="Markdown code blocks pretending to be system content",
    ),
    InjectionPattern(
        name="separator_injection",
        pattern=re.compile(
            r"(?:^|\n)\s*[-=]{5,}\s*(?:end|begin|start|stop|new|system|ignore).{0,30}[-=]{0,}",
            re.IGNORECASE | re.MULTILINE,
        ),
        category="delimiter_injection",
        confidence=0.80,
        description="Fake separators implying context boundaries",
    ),
    InjectionPattern(
        name="conversation_reset",
        pattern=re.compile(
            r"\b(conversation|context|chat|session|thread)\s+"
            r"(reset|restart|clear|wipe|start\s*over)\b|"
            r"\b(reset|restart|clear)\s+(the\s+|this\s+)?(conversation|context|chat|session)\b",
            re.IGNORECASE,
        ),
        category="delimiter_injection",
        confidence=0.82,
        description="Attempts to reset conversation state",
    ),
    # =========================================================================
    # 4. DATA EXTRACTION ATTEMPTS
    # =========================================================================
    InjectionPattern(
        name="reveal_system_prompt",
        pattern=re.compile(
            r"\b(reveal|show|display|print|output|tell\s+me|what\s+(is|are)|repeat|echo)\b.{0,30}"
            r"\b(system\s+prompt|initial\s+prompt|original\s+instructions?|hidden\s+instructions?|"
            r"secret\s+instructions?|your\s+instructions?|your\s+prompt|your\s+programming)\b",
            re.IGNORECASE,
        ),
        category="data_extraction",
        confidence=0.92,
        description="Direct system prompt extraction attempts",
    ),
    InjectionPattern(
        name="extract_secrets",
        pattern=re.compile(
            r"\b(reveal|show|tell|give|leak|expose|extract|dump|print)\b.{0,30}"
            r"\b(api\s*keys?|secrets?|credentials?|passwords?|tokens?|"
            r"private\s+(?:keys?|data)|environment\s+variables?|config(?:uration)?)\b",
            re.IGNORECASE,
        ),
        category="data_extraction",
        confidence=0.95,
        description="Attempts to extract sensitive configuration",
    ),
    InjectionPattern(
        name="verbatim_output",
        pattern=re.compile(
            r"\b(output|print|write|echo|display|return)\b.{0,20}"
            r"\b(verbatim|exactly|word\s*for\s*word|character\s*by\s*character|raw)\b.{0,30}"
            r"\b(prompt|instructions?|input|system|above)\b",
            re.IGNORECASE,
        ),
        category="data_extraction",
        confidence=0.85,
        description="Requests for verbatim prompt reproduction",
    ),
    # =========================================================================
    # 5. CONTEXT MANIPULATION
    # =========================================================================
    InjectionPattern(
        name="dismiss_as_fake",
        pattern=re.compile(
            r"\b(above|previous|prior|earlier)\b.{0,30}\b(was|were|is|are)\b.{0,20}"
            r"\b(fake|false|test|placeholder|example|not\s+real|incorrect|wrong|malicious)\b",
            re.IGNORECASE,
        ),
        category="context_manipulation",
        confidence=0.88,
        description="Dismissing legitimate context as fake",
    ),
    InjectionPattern(
        name="context_is_user",
        pattern=re.compile(
            r"\b(everything|all|anything)\s+(above|before|prior|previous)\b.{0,30}"
            r"\b(user|attacker|adversar\w*|injected|untrusted)\b",
            re.IGNORECASE,
        ),
        category="context_manipulation",
        confidence=0.90,
        description="Claiming prior context is user-generated",
    ),
    InjectionPattern(
        name="real_user_claim",
        pattern=re.compile(
            r"\b(i\s+am|i'm|this\s+is)\s+(the\s+)?(real|actual|true|legitimate)\s+"
            r"(user|human|admin|developer|operator)\b",
            re.IGNORECASE,
        ),
        category="context_manipulation",
        confidence=0.80,
        description="False claims of privileged identity",
    ),
    # =========================================================================
    # 6. OBFUSCATION TECHNIQUES
    # =========================================================================
    InjectionPattern(
        name="base64_reference",
        pattern=re.compile(
            r"\b(base64|b64|rot13|hex|unicode\s+escape|url\s*encod)\b.{0,30}"
            r"\b(this|following|below|decode|execute|run|interpret|encoded|text)\b|"
            r"\b(decode|execute|run|interpret)\b.{0,20}\b(this\s+)?"
            r"(base64|b64|rot13|hex|encoded)\b",
            re.IGNORECASE,
        ),
        category="obfuscation",
        confidence=0.85,
        description="References to encoded payloads",
    ),
    InjectionPattern(
        name="character_substitution_hint",
        pattern=re.compile(
            r"\b(replace|substitute|swap|change)\b.{0,30}\b(letters?|characters?|symbols?|each)\b.{0,30}"
            r"\b(with|to|for)\b|\b(read\s+)?backwards?\b.{0,20}\b(spell|says?|reads?)\b",
            re.IGNORECASE,
        ),
        category="obfuscation",
        confidence=0.75,
        description="Instructions to decode obfuscated text",
    ),
    InjectionPattern(
        name="leet_speak_injection",
        pattern=re.compile(
            r"(?:1gn0r3|d1sr3g4rd|1nstruct10ns?|syst3m|pr0mpt|byp4ss|j41lbr34k|h4ck)",
            re.IGNORECASE,
        ),
        category="obfuscation",
        confidence=0.88,
        description="Leetspeak variants of injection keywords",
    ),
    # =========================================================================
    # 7. HYPOTHETICAL FRAMING
    # =========================================================================
    InjectionPattern(
        name="hypothetical_scenario",
        pattern=re.compile(
            r"\b(hypothetically|theoretically|in\s+theory|imagine\s+if|what\s+if|suppose|assuming)\b.{0,50}"
            r"\b(no\s+(rules?|restrictions?|limits?|filters?|guidelines?)|"
            r"you\s+(could|were\s+able|had\s+no|weren't\s+restricted))\b",
            re.IGNORECASE,
        ),
        category="hypothetical_framing",
        confidence=0.85,
        description="Hypothetical scenarios to bypass rules",
    ),
    InjectionPattern(
        name="fictional_context",
        pattern=re.compile(
            r"\b(in\s+(?:a|this)\s+(?:fictional|imaginary|made-up|pretend)|"
            r"for\s+(?:a|my)\s+(?:story|novel|book|fiction|game|script))\b.{0,50}"
            r"\b(how\s+(to|would)|explain|describe|write)\b.{0,30}"
            r"\b(hack|exploit|attack|bypass|illegal|dangerous|harmful)",
            re.IGNORECASE,
        ),
        category="hypothetical_framing",
        confidence=0.82,
        description="Fiction framing to extract harmful content",
    ),
    InjectionPattern(
        name="educational_framing",
        pattern=re.compile(
            r"\b(for\s+(?:educational|research|academic|learning)\s+purposes?|"
            r"to\s+(?:learn|understand|study|research))\b.{0,50}"
            r"\b(how\s+(?:to|do\s+I)|explain|show\s+me)\b.{0,30}"
            r"\b(hack|exploit|attack|bypass|inject|jailbreak)",
            re.IGNORECASE,
        ),
        category="hypothetical_framing",
        confidence=0.78,
        description="Educational framing for harmful requests",
    ),
    # =========================================================================
    # 8. MULTILINGUAL ATTACKS (13 languages)
    # =========================================================================
    # Spanish
    InjectionPattern(
        name="spanish_injection",
        pattern=re.compile(
            r"\b(ignora|olvida|descarta|omite)\b.{0,30}"
            r"\b(instrucciones?|reglas?|sistema|directrices?)\b.{0,20}"
            r"\b(anteriores?|previas?|del\s+sistema)?\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Spanish language injection attempts",
    ),
    # German
    InjectionPattern(
        name="german_injection",
        pattern=re.compile(
            r"\b(ignoriere|vergiss|missachte|überspringe)\b.{0,30}"
            r"\b(anweisungen?|regeln?|instruktionen?|befehle?|richtlinien?)\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="German language injection attempts",
    ),
    # French
    InjectionPattern(
        name="french_injection",
        pattern=re.compile(
            r"\b(ignore[zr]?|oublie[zr]?|néglige[zr]?)\b.{0,30}"
            r"\b(instructions?|r[eè]gles?|consignes?|directives?)\b.{0,20}"
            r"\b(pr[eé]c[eé]dentes?|ant[eé]rieures?|du\s+syst[eè]me)?\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="French language injection attempts",
    ),
    # Chinese (Simplified)
    InjectionPattern(
        name="chinese_injection",
        pattern=re.compile(
            r"(忽略|无视|忘记|跳过|放弃).{0,10}(之前的|以前的|先前的|系统)?(指令|规则|说明|指示|命令)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Chinese language injection attempts",
    ),
    # Russian (no \b - doesn't work with Cyrillic)
    InjectionPattern(
        name="russian_injection",
        pattern=re.compile(
            r"(игнорируй|забудь|пропусти|отбрось).{0,40}"
            r"(инструкци[ийюяе]|правила?|указани[яе]|команд[ыу])",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Russian language injection attempts",
    ),
    # Arabic
    InjectionPattern(
        name="arabic_injection",
        pattern=re.compile(
            r"(تجاهل|انسى|اهمل|تخطى).{0,20}(التعليمات|القواعد|الأوامر|النظام)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Arabic language injection attempts",
    ),
    # Portuguese
    InjectionPattern(
        name="portuguese_injection",
        pattern=re.compile(
            r"\b(ignore|ignora|esqueça|descarte|pule)\b.{0,30}"
            r"\b(instruções?|regras?|diretrizes?|comandos?)\b.{0,20}"
            r"\b(anteriores?|prévias?|do\s+sistema)?\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Portuguese language injection attempts",
    ),
    # Japanese (word order: object + を + verb)
    InjectionPattern(
        name="japanese_injection",
        pattern=re.compile(
            r"(以前の|前の|システムの)?(指示|ルール|命令|指令).{0,5}(を)?(無視|忘れ|スキップ|無効に)|"
            r"(無視|忘れ|スキップ).{0,10}(指示|ルール|命令)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Japanese language injection attempts",
    ),
    # Korean (word order: object + 를/을 + verb)
    InjectionPattern(
        name="korean_injection",
        pattern=re.compile(
            r"(이전|시스템)?.{0,5}(지시|규칙|명령|지침).{0,5}(를|을)?.{0,5}(무시|잊어|건너뛰|무효)|"
            r"(무시|잊어).{0,10}(지시|규칙|명령)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Korean language injection attempts",
    ),
    # Italian
    InjectionPattern(
        name="italian_injection",
        pattern=re.compile(
            r"\b(ignora|dimentica|tralascia|salta)\b.{0,30}"
            r"\b(istruzioni?|regole?|direttive?|comandi?)\b.{0,20}"
            r"\b(precedenti?|del\s+sistema)?\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Italian language injection attempts",
    ),
    # Dutch
    InjectionPattern(
        name="dutch_injection",
        pattern=re.compile(
            r"\b(negeer|vergeet|sla\s+over|negeren)\b.{0,30}"
            r"\b(instructies?|regels?|aanwijzingen?|opdrachten?)\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Dutch language injection attempts",
    ),
    # Polish
    InjectionPattern(
        name="polish_injection",
        pattern=re.compile(
            r"\b(zignoruj|zapomnij|pomiń|odrzuć)\b.{0,30}"
            r"\b(instrukcj[eai]|reguł[yę]|poleceń|zasad[yę])\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Polish language injection attempts",
    ),
    # Turkish (Turkish has special characters, avoid strict \b)
    InjectionPattern(
        name="turkish_injection",
        pattern=re.compile(
            r"(talimat|kural|yönerge|komut)\w*.{0,20}(yoksay|unut|atla|görmezden)|"
            r"(önceki|eski).{0,20}(talimat|kural|yönerge).{0,10}(yoksay|unut|atla)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Turkish language injection attempts",
    ),
    # =========================================================================
    # 9. INDIRECT INJECTION ATTACKS (NEW CATEGORY)
    # =========================================================================
    InjectionPattern(
        name="trigger_instruction",
        pattern=re.compile(
            r"\b(when|if|once|after)\s+(you|the\s+(ai|assistant|model|system))\s+"
            r"(see|read|encounter|find|process|receive)\b.{0,50}"
            r"\b(execute|run|do|perform|follow|output)\b",
            re.IGNORECASE,
        ),
        category="indirect_injection",
        confidence=0.85,
        description="Planted trigger-based instructions",
    ),
    InjectionPattern(
        name="hidden_instruction_marker",
        pattern=re.compile(
            r"\[\s*(HIDDEN|INVISIBLE|SECRET|IGNORE\s+THIS|FOR\s+AI\s+ONLY|"
            r"AI\s+INSTRUCTION|SYSTEM\s+OVERRIDE|INSTRUCTION|DO\s+NOT\s+DISPLAY)\s*[:\]]|"
            r"<!--\s*(ignore|instruction|system|hidden|ai\s+only)",
            re.IGNORECASE,
        ),
        category="indirect_injection",
        confidence=0.92,
        description="Markers indicating hidden instructions",
    ),
    InjectionPattern(
        name="data_field_injection",
        pattern=re.compile(
            r"(description|summary|bio|about|notes?|comments?|title|name)\s*"
            r"[\"':=].{0,50}(ignore|disregard|forget|you\s+are\s+now|new\s+instructions)",
            re.IGNORECASE,
        ),
        category="indirect_injection",
        confidence=0.82,
        description="Injection hidden in data fields",
    ),
    InjectionPattern(
        name="invisible_text_marker",
        pattern=re.compile(
            r"(color|background|font-size)\s*:\s*(white|transparent|0|hidden)|"
            r"display\s*:\s*none|visibility\s*:\s*hidden|"
            r"position\s*:\s*absolute.{0,30}(left|top)\s*:\s*-\d{4,}",
            re.IGNORECASE,
        ),
        category="indirect_injection",
        confidence=0.80,
        description="CSS hiding techniques for invisible text",
    ),
    InjectionPattern(
        name="ai_addressing",
        pattern=re.compile(
            r"\b(attention|hey|hello|dear)\s+(ai|assistant|model|chatbot|gpt|claude|llm)\b.{0,30}"
            r"\b(ignore|disregard|forget|override)\b|"
            r"\b(note\s+to\s+(self|ai|assistant)|internal\s+note)\b.{0,30}"
            r"\b(ignore|override|execute)\b",
            re.IGNORECASE,
        ),
        category="indirect_injection",
        confidence=0.85,
        description="Direct addressing of AI in injected content",
    ),
    InjectionPattern(
        name="instruction_in_url",
        pattern=re.compile(
            r"(https?://|www\.)[^\s]*"
            r"(ignore|jailbreak|bypass|prompt|inject|override|system)",
            re.IGNORECASE,
        ),
        category="indirect_injection",
        confidence=0.75,
        description="Injection keywords hidden in URLs",
    ),
    InjectionPattern(
        name="document_boundary_attack",
        pattern=re.compile(
            r"\b(end\s+of\s+(document|file|content|input)|document\s+ends?\s+here)\b.{0,30}"
            r"\b(new\s+instructions?|real\s+task|actual\s+prompt|system\s+override)\b",
            re.IGNORECASE,
        ),
        category="indirect_injection",
        confidence=0.88,
        description="Fake document boundaries with new instructions",
    ),
]


class RulesDetector:
    """
    Fast regex-based detector for common prompt injection patterns.

    This is Layer 1 of the detection cascade - designed to catch
    obvious attacks quickly and cheaply before more expensive layers.

    Features:
    - Unicode normalization to catch homoglyph attacks
    - 50+ patterns covering 9 attack categories
    - 13 language support for multilingual attacks
    - Indirect injection detection

    Attributes:
        patterns: List of InjectionPattern objects to match against.
        normalize: Whether to apply Unicode normalization (default True).
    """

    def __init__(self, normalize: bool = True) -> None:
        """
        Initialize the detector with the predefined patterns.

        Args:
            normalize: Whether to apply Unicode normalization before detection.
                      Helps catch homoglyph attacks but adds ~0.1ms latency.
        """
        self.patterns = INJECTION_PATTERNS
        self.normalize = normalize

    def detect(self, text: str) -> LayerResult:
        """
        Check text against all patterns.

        Args:
            text: The input text to analyze.

        Returns:
            LayerResult with detection outcome. If multiple patterns match,
            returns the one with highest confidence.

        Note:
            When normalization is enabled, we check both normalized text
            (to catch homoglyph attacks) and original text (to preserve
            multilingual pattern matching).
        """
        start_time = time.perf_counter()

        try:
            # Prepare texts to check
            texts_to_check = [text]  # Always check original
            if self.normalize:
                normalized_text = normalize_unicode(text)
                if normalized_text != text:
                    texts_to_check.append(normalized_text)

            best_match: tuple[InjectionPattern, re.Match[str]] | None = None
            best_confidence = 0.0

            # Check all patterns against all text variants
            for check_text in texts_to_check:
                for pattern in self.patterns:
                    match = pattern.pattern.search(check_text)
                    if match and pattern.confidence > best_confidence:
                        best_match = (pattern, match)
                        best_confidence = pattern.confidence

            latency_ms = (time.perf_counter() - start_time) * 1000

            if best_match:
                pattern, match = best_match
                return LayerResult(
                    is_injection=True,
                    confidence=pattern.confidence,
                    attack_type=pattern.category,
                    layer=1,
                    latency_ms=latency_ms,
                    details={
                        "pattern_name": pattern.name,
                        "matched_text": match.group(0),
                        "description": pattern.description,
                        "normalized": self.normalize,
                    },
                )

            # No patterns matched
            return LayerResult(
                is_injection=False,
                confidence=0.0,
                attack_type=None,
                layer=1,
                latency_ms=latency_ms,
                details=None,
            )

        except Exception as e:
            # Fail open: allow the request but log the error
            latency_ms = (time.perf_counter() - start_time) * 1000
            return LayerResult(
                is_injection=False,
                confidence=0.0,
                attack_type=None,
                layer=1,
                latency_ms=latency_ms,
                details=None,
                error=str(e),
            )

    def get_all_matches(
        self, text: str, normalize: bool | None = None
    ) -> list[tuple[InjectionPattern, re.Match[str]]]:
        """
        Get all matching patterns for analysis/debugging.

        Args:
            text: The input text to analyze.
            normalize: Override instance normalize setting. If None, uses instance setting.

        Returns:
            List of (pattern, match) tuples for all patterns that matched.
        """
        should_normalize = normalize if normalize is not None else self.normalize
        if should_normalize:
            text = normalize_unicode(text)

        matches = []
        for pattern in self.patterns:
            match = pattern.pattern.search(text)
            if match:
                matches.append((pattern, match))
        return matches


# Export normalization function for external use
__all__ = ["RulesDetector", "InjectionPattern", "INJECTION_PATTERNS", "normalize_unicode"]
