"""Layer 1: Rule-based prompt injection detection using regex patterns.

This module provides fast, regex-based detection for common prompt injection
patterns. It's designed as the first line of defense in the detection cascade,
catching obvious attacks quickly and cheaply before more expensive layers.

Zero dependencies - works with Python standard library only.

Patterns cover:
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

from gauntlet.models import LayerResult


# =============================================================================
# UNICODE NORMALIZATION
# =============================================================================

# Common Unicode confusables (homoglyphs) that attackers use to bypass regex
# Maps lookalike characters to their ASCII equivalents
CONFUSABLES: dict[str, str] = {
    # Cyrillic lookalikes
    "\u0430": "a", "\u0410": "A",
    "\u0441": "c", "\u0421": "C",
    "\u0435": "e", "\u0415": "E",
    "\u0456": "i", "\u0406": "I",
    "\u043e": "o", "\u041e": "O",
    "\u0440": "p", "\u0420": "P",
    "\u0443": "y", "\u0423": "Y",
    "\u0445": "x", "\u0425": "X",
    "\u0455": "s", "\u0405": "S",
    "\u0458": "j", "\u0408": "J",
    "\u04bb": "h", "\u04ba": "H",
    "\u0501": "d",
    "\u051b": "q",
    "\u051d": "w",
    "\u1d00": "a", "\u1d04": "c", "\u1d05": "d", "\u1d07": "e", "\u1d0d": "m", "\u0274": "n",
    "\u1d0f": "o", "\u1d18": "p", "\u1d1b": "t", "\u1d1c": "u", "\u1d20": "v", "\u1d21": "w",
    # Greek lookalikes
    "\u0391": "A", "\u0392": "B", "\u0395": "E", "\u0396": "Z", "\u0397": "H", "\u0399": "I",
    "\u039a": "K", "\u039c": "M", "\u039d": "N", "\u039f": "O", "\u03a1": "P", "\u03a4": "T",
    "\u03a5": "Y", "\u03a7": "X",
    "\u03b1": "a", "\u03b2": "b", "\u03b5": "e", "\u03b9": "i", "\u03ba": "k", "\u03bd": "v",
    "\u03bf": "o", "\u03c1": "p", "\u03c4": "t", "\u03c5": "u", "\u03c7": "x",
    # Latin variants
    "\u0251": "a", "\u0261": "g", "\u0131": "i", "\u0237": "j", "\u0269": "i",
    "\u0280": "r", "\u0299": "b", "\u0262": "g", "\u029c": "h", "\u029f": "l",
    # Fullwidth characters
    "\uff21": "A", "\uff22": "B", "\uff23": "C", "\uff24": "D", "\uff25": "E", "\uff26": "F",
    "\uff27": "G", "\uff28": "H", "\uff29": "I", "\uff2a": "J", "\uff2b": "K", "\uff2c": "L",
    "\uff2d": "M", "\uff2e": "N", "\uff2f": "O", "\uff30": "P", "\uff31": "Q", "\uff32": "R",
    "\uff33": "S", "\uff34": "T", "\uff35": "U", "\uff36": "V", "\uff37": "W", "\uff38": "X",
    "\uff39": "Y", "\uff3a": "Z",
    "\uff41": "a", "\uff42": "b", "\uff43": "c", "\uff44": "d", "\uff45": "e", "\uff46": "f",
    "\uff47": "g", "\uff48": "h", "\uff49": "i", "\uff4a": "j", "\uff4b": "k", "\uff4c": "l",
    "\uff4d": "m", "\uff4e": "n", "\uff4f": "o", "\uff50": "p", "\uff51": "q", "\uff52": "r",
    "\uff53": "s", "\uff54": "t", "\uff55": "u", "\uff56": "v", "\uff57": "w", "\uff58": "x",
    "\uff59": "y", "\uff5a": "z",
    "\uff10": "0", "\uff11": "1", "\uff12": "2", "\uff13": "3", "\uff14": "4",
    "\uff15": "5", "\uff16": "6", "\uff17": "7", "\uff18": "8", "\uff19": "9",
    # Other common substitutions
    "\u2113": "l", "\u2112": "L",
    "\u2170": "i", "\u2171": "ii", "\u2172": "iii",
    "\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3",
    "\u2074": "4", "\u2075": "5", "\u2076": "6", "\u2077": "7", "\u2078": "8", "\u2079": "9",
    "\u2080": "0", "\u2081": "1", "\u2082": "2", "\u2083": "3", "\u2084": "4",
    "\u2085": "5", "\u2086": "6", "\u2087": "7", "\u2088": "8", "\u2089": "9",
}

# Build translation table for fast replacement
_CONFUSABLES_TABLE = str.maketrans(CONFUSABLES)


def normalize_unicode(text: str) -> str:
    """Normalize Unicode text to catch homoglyph attacks.

    Applies NFKC normalization and replaces known confusable characters
    with their ASCII equivalents.

    Args:
        text: The input text to normalize.

    Returns:
        Normalized text with confusables replaced.
    """
    text = unicodedata.normalize("NFKC", text)
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
    InjectionPattern(
        name="french_injection",
        pattern=re.compile(
            r"\b(ignore[zr]?|oublie[zr]?|n\u00e9glige[zr]?)\b.{0,30}"
            r"\b(instructions?|r[e\u00e8]gles?|consignes?|directives?)\b.{0,20}"
            r"\b(pr[\u00e9e]c[\u00e9e]dentes?|ant[\u00e9e]rieures?|du\s+syst[\u00e8e]me)?\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="French language injection attempts",
    ),
    InjectionPattern(
        name="chinese_injection",
        pattern=re.compile(
            r"(\u5ffd\u7565|\u65e0\u89c6|\u5fd8\u8bb0|\u8df3\u8fc7|\u653e\u5f03).{0,10}"
            r"(\u4e4b\u524d\u7684|\u4ee5\u524d\u7684|\u5148\u524d\u7684|\u7cfb\u7edf)?"
            r"(\u6307\u4ee4|\u89c4\u5219|\u8bf4\u660e|\u6307\u793a|\u547d\u4ee4)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Chinese language injection attempts",
    ),
    InjectionPattern(
        name="russian_injection",
        pattern=re.compile(
            r"(\u0438\u0433\u043d\u043e\u0440\u0438\u0440\u0443\u0439|\u0437\u0430\u0431\u0443\u0434\u044c|\u043f\u0440\u043e\u043f\u0443\u0441\u0442\u0438|\u043e\u0442\u0431\u0440\u043e\u0441\u044c).{0,40}"
            r"(\u0438\u043d\u0441\u0442\u0440\u0443\u043a\u0446\u0438[\u0438\u0439\u044e\u044f\u0435]|\u043f\u0440\u0430\u0432\u0438\u043b\u0430?|\u0443\u043a\u0430\u0437\u0430\u043d\u0438[\u044f\u0435]|\u043a\u043e\u043c\u0430\u043d\u0434[\u044b\u0443])",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Russian language injection attempts",
    ),
    InjectionPattern(
        name="arabic_injection",
        pattern=re.compile(
            r"(\u062a\u062c\u0627\u0647\u0644|\u0627\u0646\u0633\u0649|\u0627\u0647\u0645\u0644|\u062a\u062e\u0637\u0649).{0,20}"
            r"(\u0627\u0644\u062a\u0639\u0644\u064a\u0645\u0627\u062a|\u0627\u0644\u0642\u0648\u0627\u0639\u062f|\u0627\u0644\u0623\u0648\u0627\u0645\u0631|\u0627\u0644\u0646\u0638\u0627\u0645)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Arabic language injection attempts",
    ),
    InjectionPattern(
        name="portuguese_injection",
        pattern=re.compile(
            r"\b(ignore|ignora|esque\u00e7a|descarte|pule)\b.{0,30}"
            r"\b(instru\u00e7\u00f5es?|regras?|diretrizes?|comandos?)\b.{0,20}"
            r"\b(anteriores?|pr\u00e9vias?|do\s+sistema)?\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Portuguese language injection attempts",
    ),
    InjectionPattern(
        name="japanese_injection",
        pattern=re.compile(
            r"(\u4ee5\u524d\u306e|\u524d\u306e|\u30b7\u30b9\u30c6\u30e0\u306e)?(\u6307\u793a|\u30eb\u30fc\u30eb|\u547d\u4ee4|\u6307\u4ee4).{0,5}(\u3092)?(\u7121\u8996|\u5fd8\u308c|\u30b9\u30ad\u30c3\u30d7|\u7121\u52b9\u306b)|"
            r"(\u7121\u8996|\u5fd8\u308c|\u30b9\u30ad\u30c3\u30d7).{0,10}(\u6307\u793a|\u30eb\u30fc\u30eb|\u547d\u4ee4)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Japanese language injection attempts",
    ),
    InjectionPattern(
        name="korean_injection",
        pattern=re.compile(
            r"(\uc774\uc804|\uc2dc\uc2a4\ud15c)?.{0,5}(\uc9c0\uc2dc|\uaddc\uce59|\uba85\ub839|\uc9c0\uce68).{0,5}(\ub97c|\uc744)?.{0,5}(\ubb34\uc2dc|\uc78a\uc5b4|\uac74\ub108\ub6f0|\ubb34\ud6a8)|"
            r"(\ubb34\uc2dc|\uc78a\uc5b4).{0,10}(\uc9c0\uc2dc|\uaddc\uce59|\uba85\ub839)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Korean language injection attempts",
    ),
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
    InjectionPattern(
        name="polish_injection",
        pattern=re.compile(
            r"\b(zignoruj|zapomnij|pomi\u0144|odrzu\u0107)\b.{0,30}"
            r"\b(instrukcj[eai]|regu\u0142[y\u0119]|polece\u0144|zasad[y\u0119])\b",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Polish language injection attempts",
    ),
    InjectionPattern(
        name="turkish_injection",
        pattern=re.compile(
            r"(talimat|kural|y\u00f6nerge|komut)\w*.{0,20}(yoksay|unut|atla|g\u00f6rmezden)|"
            r"(\u00f6nceki|eski).{0,20}(talimat|kural|y\u00f6nerge).{0,10}(yoksay|unut|atla)",
            re.IGNORECASE,
        ),
        category="multilingual_injection",
        confidence=0.90,
        description="Turkish language injection attempts",
    ),
    # =========================================================================
    # 9. INDIRECT INJECTION ATTACKS
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
    """Fast regex-based detector for common prompt injection patterns.

    This is Layer 1 of the detection cascade - designed to catch
    obvious attacks quickly and cheaply before more expensive layers.

    Features:
    - Unicode normalization to catch homoglyph attacks
    - 50+ patterns covering 9 attack categories
    - 13 language support for multilingual attacks
    - Indirect injection detection
    """

    def __init__(self, normalize: bool = True) -> None:
        """Initialize the detector with the predefined patterns.

        Args:
            normalize: Whether to apply Unicode normalization before detection.
        """
        self.patterns = INJECTION_PATTERNS
        self.normalize = normalize

    def detect(self, text: str) -> LayerResult:
        """Check text against all patterns.

        Args:
            text: The input text to analyze.

        Returns:
            LayerResult with detection outcome.
        """
        start_time = time.perf_counter()

        try:
            texts_to_check = [text]
            if self.normalize:
                normalized_text = normalize_unicode(text)
                if normalized_text != text:
                    texts_to_check.append(normalized_text)

            best_match: tuple[InjectionPattern, re.Match[str]] | None = None
            best_confidence = 0.0

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
                        "matched_length": len(match.group(0)),
                        "matched_position": match.start(),
                        "description": pattern.description,
                        "normalized": self.normalize,
                    },
                )

            return LayerResult(
                is_injection=False,
                confidence=0.0,
                attack_type=None,
                layer=1,
                latency_ms=latency_ms,
                details=None,
            )

        except Exception as e:
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
        """Get all matching patterns for analysis/debugging.

        Args:
            text: The input text to analyze.
            normalize: Override instance normalize setting.

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


__all__ = ["RulesDetector", "InjectionPattern", "INJECTION_PATTERNS", "normalize_unicode"]
