"""
Pith Optimizer — Rule-based prompt optimization.

Open-source core: regex patterns, dedup, whitespace normalization.
Supports 6 languages: EN, DE, ES, FR, IT, TR.

Strategies:
1. Whitespace normalization
2. System prompt deduplication
3. Verbose phrase compression (multilingual)
4. Filler & hedge word removal (multilingual)
5. Redundant instruction stripping
6. Conversation history compaction (basic truncation)
7. Repeated sentence detection
8. Markdown overhead stripping
9. Negative savings guard
10. Auto language detection

For AI-powered compression (LLMLingua-2, Pith Distill),
see pithtoken.ai/docs or install: pip install pith[ml]
"""

import hashlib
import re

from .config import get_settings
from .injection import InjectionResult, check_messages, sanitize_prompt

settings = get_settings()

# --- Language detection (lightweight, no dependencies) ---
# Common words used to detect language — checked against first 500 chars of text
_LANG_MARKERS: dict[str, list[str]] = {
    "de": ["der", "die", "das", "und", "ist", "ein", "eine", "nicht", "ich", "sie",
           "mit", "auf", "für", "den", "von", "werden", "dass", "auch", "nach", "wie",
           "aber", "noch", "kann", "wenn", "sind", "wird", "oder", "seine", "haben"],
    "es": ["el", "la", "los", "las", "que", "por", "una", "del", "para", "con",
           "como", "pero", "más", "esta", "todo", "sobre", "puede", "entre", "desde",
           "porque", "también", "tiene", "esto", "cuando", "hacer", "muy", "hasta",
           "cómo", "necesito", "explicar", "ayudar", "entender", "sistema", "funciona",
           "me", "crear", "gustaría", "podrías"],
    "fr": ["le", "la", "les", "des", "est", "une", "que", "dans", "pas", "pour",
           "qui", "sur", "avec", "sont", "mais", "nous", "vous", "cette", "tout",
           "peut", "aussi", "fait", "comme", "être", "avoir", "plus", "entre"],
    "it": ["il", "la", "che", "non", "una", "per", "con", "sono", "della", "anche",
           "come", "questo", "più", "nel", "dei", "gli", "alla", "essere", "tutti",
           "molto", "stato", "già", "ogni", "dove", "dopo", "ancora", "fare", "tra"],
    "tr": ["bir", "ve", "bu", "için", "ile", "olan", "olarak", "gibi", "daha",
           "ancak", "çok", "ama", "sonra", "kadar", "nasıl", "üzerinde", "bunu",
           "değil", "yapı", "olan", "başka", "hala", "neden", "veya", "ayrıca",
           # Standalone words common in Turkish prompts (not found in other langs)
           "sen", "yanıt", "emin", "hiçbir", "şey", "doğru", "zaman", "her",
           "lütfen", "mısın", "misin", "olmalı", "ekleme", "listele", "açıkla",
           "yardımcı", "cevap", "bilgi", "örnek", "kullan"],
}


def _detect_language(text: str) -> str:
    """Detect language from text. Returns 'en' as default.
    Lightweight: checks word frequency in first 800 chars, <0.1ms.
    """
    sample = text[:800].lower()
    # Extract words — broad Unicode letter support for accented chars
    words = set(re.findall(r"\b\w+\b", sample))

    best_lang = "en"
    best_score = 0

    for lang, markers in _LANG_MARKERS.items():
        score = sum(1 for m in markers if m in words)
        if score > best_score:
            best_score = score
            best_lang = lang

    # Need at least 2 marker matches to switch from English
    return best_lang if best_score >= 2 else "en"


# --- Prompt cache (avoid re-optimizing identical prompts) ---
_cache: dict[str, str] = {}
_CACHE_MAX = 2048

# --- LLM compression cache (separate, for system prompts) ---
_llm_cache: dict[str, str] = {}
_LLM_CACHE_MAX = 512


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# --- PASS 1: Filler / hedge words (removed FIRST so verbose patterns match cleanly) ---
FILLER_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bbasically\s+", re.I), ""),
    (re.compile(r"\bessentially\s+", re.I), ""),
    (re.compile(r"\bactually\s+", re.I), ""),
    (re.compile(r"\bliterally\s+", re.I), ""),
    (re.compile(r"\bvery\s+", re.I), ""),
    (re.compile(r"\breally\s+", re.I), ""),
    (re.compile(r"\bjust\s+", re.I), ""),
    (re.compile(r"\bsimply\s+", re.I), ""),
    (re.compile(r"\bquite\s+", re.I), ""),
    (re.compile(r"\brather\s+", re.I), ""),
    (re.compile(r"\bsomewhat\s+", re.I), ""),
    (re.compile(r"\bperhaps\s+", re.I), ""),
    (re.compile(r"\bpossibly\s+", re.I), ""),
    (re.compile(r"\bkindly\s+", re.I), ""),
    (re.compile(r"\bcertainly\s+", re.I), ""),
    (re.compile(r"\bdefinitely\s+", re.I), ""),
    (re.compile(r"\bobviously\s+", re.I), ""),
    (re.compile(r"\bclearly\s+", re.I), ""),
    (re.compile(r"\bhonestly\s+", re.I), ""),
    (re.compile(r"\bfrankly\s+", re.I), ""),
    (re.compile(r"\bpersonally\s+", re.I), ""),
]

# --- German (DE) Filler Patterns ---
FILLER_PATTERNS_DE: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\beigentlich\s+", re.I), ""),
    (re.compile(r"\bgrundsätzlich\s+", re.I), ""),
    (re.compile(r"\bsozusagen\s+", re.I), ""),
    (re.compile(r"\bpraktisch\s+", re.I), ""),
    (re.compile(r"\btatsächlich\s+", re.I), ""),
    (re.compile(r"\bim Grunde\s+", re.I), ""),
    (re.compile(r"\bim Prinzip\s+", re.I), ""),
    (re.compile(r"\bquasi\s+", re.I), ""),
    (re.compile(r"\bziemlich\s+", re.I), ""),
    (re.compile(r"\bwirklich\s+", re.I), ""),
    (re.compile(r"\bdurchaus\s+", re.I), ""),
    (re.compile(r"\bnun\s+", re.I), ""),
    (re.compile(r"\bhalt\s+", re.I), ""),
    (re.compile(r"\beben\s+", re.I), ""),
    (re.compile(r"\bnaja\s*,?\s*", re.I), ""),
    (re.compile(r"\bna ja\s*,?\s*", re.I), ""),
    (re.compile(r"\bgewissermaßen\s+", re.I), ""),
    (re.compile(r"\bselbstverständlich\s+", re.I), ""),
    (re.compile(r"\bnatürlich\s+", re.I), ""),
    (re.compile(r"\boffensichtlich\s+", re.I), ""),
    (re.compile(r"\beinfach\s+", re.I), ""),
    (re.compile(r"\bvielleicht\s+", re.I), ""),
    (re.compile(r"\bmöglicherweise\s+", re.I), ""),
    (re.compile(r"\bsicherlich\s+", re.I), ""),
    (re.compile(r"\behrlich gesagt\s*,?\s*", re.I), ""),
]

# --- Spanish (ES) Filler Patterns ---
FILLER_PATTERNS_ES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bbásicamente\s+", re.I), ""),
    (re.compile(r"\besencialmente\s+", re.I), ""),
    (re.compile(r"\ben realidad\s+", re.I), ""),
    (re.compile(r"\brealmente\s+", re.I), ""),
    (re.compile(r"\bsimplemente\s+", re.I), ""),
    (re.compile(r"\bprácticamente\s+", re.I), ""),
    (re.compile(r"\bfundamentalmente\s+", re.I), ""),
    (re.compile(r"\bsinceramente\s+", re.I), ""),
    (re.compile(r"\bfrancamente\s+", re.I), ""),
    (re.compile(r"\bobviamente\s+", re.I), ""),
    (re.compile(r"\bclaramente\s+", re.I), ""),
    (re.compile(r"\bdefinitivamente\s+", re.I), ""),
    (re.compile(r"\bpersonalmente\s+", re.I), ""),
    (re.compile(r"\bciertamente\s+", re.I), ""),
    (re.compile(r"\btal vez\s+", re.I), ""),
    (re.compile(r"\bquizás\s+", re.I), ""),
    (re.compile(r"\bposiblemente\s+", re.I), ""),
    (re.compile(r"\bde hecho\s*,?\s*", re.I), ""),
    (re.compile(r"\bpor supuesto\s*,?\s*", re.I), ""),
    (re.compile(r"\bla verdad es que\s+", re.I), ""),
    (re.compile(r"\bdigamos que\s+", re.I), ""),
    (re.compile(r"\bo sea\s*,?\s*", re.I), ""),
    (re.compile(r"\bbueno\s*,?\s*", re.I), ""),
    (re.compile(r"\bpues\s*,?\s*", re.I), ""),
]

# --- French (FR) Filler Patterns ---
FILLER_PATTERNS_FR: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bessentiellement\s+", re.I), ""),
    (re.compile(r"\bfondamentalement\s+", re.I), ""),
    (re.compile(r"\ben fait\s*,?\s*", re.I), ""),
    (re.compile(r"\bvraiment\s+", re.I), ""),
    (re.compile(r"\bsimplement\s+", re.I), ""),
    (re.compile(r"\bpratiquement\s+", re.I), ""),
    (re.compile(r"\bfranchement\s*,?\s*", re.I), ""),
    (re.compile(r"\bsincèrement\s*,?\s*", re.I), ""),
    (re.compile(r"\bévidemment\s+", re.I), ""),
    (re.compile(r"\bclairement\s+", re.I), ""),
    (re.compile(r"\bcertainement\s+", re.I), ""),
    (re.compile(r"\bdéfinitivement\s+", re.I), ""),
    (re.compile(r"\bpersonnellement\s*,?\s*", re.I), ""),
    (re.compile(r"\bpeut-être\s+", re.I), ""),
    (re.compile(r"\bpossiblement\s+", re.I), ""),
    (re.compile(r"\bjustement\s+", re.I), ""),
    (re.compile(r"\bbon ben\s*,?\s*", re.I), ""),
    (re.compile(r"\balors\s*,?\s*", re.I), ""),
    (re.compile(r"\benfin\s*,?\s*", re.I), ""),
    (re.compile(r"\beh bien\s*,?\s*", re.I), ""),
    (re.compile(r"\bdu coup\s*,?\s*", re.I), ""),
    (re.compile(r"\bgenre\s+", re.I), ""),
    (re.compile(r"\bquoi\s*[,.]?\s*", re.I), ""),
    (re.compile(r"\ben quelque sorte\s*,?\s*", re.I), ""),
    (re.compile(r"\bà vrai dire\s*,?\s*", re.I), ""),
]

# --- Italian (IT) Filler Patterns ---
FILLER_PATTERNS_IT: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bpraticamente\s+", re.I), ""),
    (re.compile(r"\bfondamentalmente\s+", re.I), ""),
    (re.compile(r"\bessenzialmente\s+", re.I), ""),
    (re.compile(r"\beffettivamente\s+", re.I), ""),
    (re.compile(r"\bveramente\s+", re.I), ""),
    (re.compile(r"\bsemplicemente\s+", re.I), ""),
    (re.compile(r"\bsicuramente\s+", re.I), ""),
    (re.compile(r"\bcertamente\s+", re.I), ""),
    (re.compile(r"\bovviamente\s+", re.I), ""),
    (re.compile(r"\bchiaramente\s+", re.I), ""),
    (re.compile(r"\bfrancamente\s*,?\s*", re.I), ""),
    (re.compile(r"\bpersonalmente\s*,?\s*", re.I), ""),
    (re.compile(r"\bforse\s+", re.I), ""),
    (re.compile(r"\bmagari\s+", re.I), ""),
    (re.compile(r"\ballora\s*,?\s*", re.I), ""),
    (re.compile(r"\bcioè\s*,?\s*", re.I), ""),
    (re.compile(r"\becco\s*,?\s*", re.I), ""),
    (re.compile(r"\btipo\s+", re.I), ""),
    (re.compile(r"\binsomma\s*,?\s*", re.I), ""),
    (re.compile(r"\bin realtà\s*,?\s*", re.I), ""),
    (re.compile(r"\bper così dire\s*,?\s*", re.I), ""),
    (re.compile(r"\ba dire il vero\s*,?\s*", re.I), ""),
    (re.compile(r"\bin effetti\s*,?\s*", re.I), ""),
]

# --- Turkish (TR) Filler Patterns ---
FILLER_PATTERNS_TR: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\baslında\s+", re.I), ""),
    (re.compile(r"\btemelde\s+", re.I), ""),
    (re.compile(r"\bbasitçe\s+", re.I), ""),
    (re.compile(r"\bgerçekten\s+", re.I), ""),
    (re.compile(r"\bsadece\s+", re.I), ""),
    (re.compile(r"\baçıkçası\s*,?\s*", re.I), ""),
    (re.compile(r"\bkesinlikle\s+", re.I), ""),
    (re.compile(r"\bmuhtemelen\s+", re.I), ""),
    (re.compile(r"\bbüyük ihtimalle\s+", re.I), ""),
    (re.compile(r"\bbelki\s+", re.I), ""),
    (re.compile(r"\byani\b\s*,?\s*", re.I), ""),
    (re.compile(r"\bhani\b\s*,?\s*", re.I), ""),
    (re.compile(r"\bişte\b\s+", re.I), ""),
    (re.compile(r"\bayrıca\s+", re.I), ""),
    (re.compile(r"\btabii ki\s*,?\s*", re.I), ""),
    (re.compile(r"\btabii\s*,?\s*", re.I), ""),
    (re.compile(r"\belbette\s*,?\s*", re.I), ""),
    (re.compile(r"\bözellikle\s+", re.I), ""),
    (re.compile(r"\bgenellikle\s+", re.I), ""),
    (re.compile(r"\bdoğrusu\s*,?\s*", re.I), ""),
    (re.compile(r"\baçıkça\s+", re.I), ""),
    (re.compile(r"\bbir nevi\s+", re.I), ""),
    (re.compile(r"\bbir bakıma\s+", re.I), ""),
]

# --- PASS 2: Verbose patterns -> concise replacements ---
VERBOSE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Polite fluff (most common in user prompts)
    (re.compile(r"\bplease\s+", re.I), ""),
    (re.compile(r"\bI would like you to\s+", re.I), ""),
    (re.compile(r"\bI want you to\s+", re.I), ""),
    (re.compile(r"\bI'd like you to\s+", re.I), ""),
    (re.compile(r"\bCould you please\s+", re.I), ""),
    (re.compile(r"\bCan you please\s+", re.I), ""),
    (re.compile(r"\bWould you please\s+", re.I), ""),
    (re.compile(r"\bI need you to\s+", re.I), ""),
    (re.compile(r"\bI would appreciate it if you could\s+", re.I), ""),
    (re.compile(r"\bI would like to know (?:about )?\s*", re.I), "Explain "),
    (re.compile(r"\bI would like to\s+", re.I), ""),
    (re.compile(r"\bIt would be great if you could\s+", re.I), ""),
    (re.compile(r"\bIt is important that you\s+", re.I), ""),
    (re.compile(r"\bMake sure to\s+", re.I), ""),
    (re.compile(r"\bPlease make sure that\s+", re.I), ""),
    (re.compile(r"\bPlease ensure that\s+", re.I), ""),
    (re.compile(r"\bPlease note that\s+", re.I), ""),
    (re.compile(r"\bPlease be aware that\s+", re.I), ""),
    (re.compile(r"\bI'm looking for\s+", re.I), "Find "),
    (re.compile(r"\bI am looking for\s+", re.I), "Find "),
    (re.compile(r"\bCould you also\s+", re.I), "Also "),
    (re.compile(r"\bCan you also\s+", re.I), "Also "),
    (re.compile(r"\bI am particularly interested in\s+", re.I), "Include "),
    (re.compile(r"\bI'm particularly interested in\s+", re.I), "Include "),
    (re.compile(r"\bI am interested in\s+", re.I), "Include "),
    (re.compile(r"\bI'm interested in\s+", re.I), "Include "),
    (re.compile(r"\bhelp me understand how to\s+", re.I), "explain how to "),
    (re.compile(r"\bhelp me understand\s+", re.I), "explain "),
    (re.compile(r"\bI was wondering if you could\s+", re.I), ""),
    (re.compile(r"\bI was wondering\s+", re.I), ""),
    (re.compile(r"\bDo you think you could\s+", re.I), ""),
    (re.compile(r"\bWould it be possible to\s+", re.I), ""),
    (re.compile(r"\bIf it's not too much trouble\s*,?\s*", re.I), ""),
    (re.compile(r"\bWhen you get a chance\s*,?\s*", re.I), ""),
    (re.compile(r"\bI'd appreciate if you could\s+", re.I), ""),
    (re.compile(r"\band also\s+", re.I), "and "),

    # Redundant connectors / wordy phrases
    (re.compile(r"\bIn order to\b", re.I), "To"),
    (re.compile(r"\bDue to the fact that\b", re.I), "Because"),
    (re.compile(r"\bAt this point in time\b", re.I), "Now"),
    (re.compile(r"\bAt this time\b", re.I), "Now"),
    (re.compile(r"\bIn the event that\b", re.I), "If"),
    (re.compile(r"\bWith regard to\b", re.I), "About"),
    (re.compile(r"\bWith respect to\b", re.I), "About"),
    (re.compile(r"\bFor the purpose of\b", re.I), "To"),
    (re.compile(r"\bIn addition to that\b", re.I), "Also"),
    (re.compile(r"\bIn addition to\b", re.I), "Also"),
    (re.compile(r"\bAs a matter of fact\b", re.I), ""),
    (re.compile(r"\bIt should be noted that\b", re.I), ""),
    (re.compile(r"\bIt is worth mentioning that\b", re.I), ""),
    (re.compile(r"\bIt is worth noting that\b", re.I), ""),
    (re.compile(r"\bAs a result of\b", re.I), "Because of"),
    (re.compile(r"\bFor the sake of\b", re.I), "For"),
    (re.compile(r"\bOn the other hand\b", re.I), "However"),
    (re.compile(r"\bIn spite of the fact that\b", re.I), "Despite"),
    (re.compile(r"\bRegardless of the fact that\b", re.I), "Despite"),
    (re.compile(r"\bTaking into consideration\b", re.I), "Considering"),
    (re.compile(r"\bTaking into account\b", re.I), "Considering"),
    (re.compile(r"\bIn the context of\b", re.I), "In"),
    (re.compile(r"\bWith the exception of\b", re.I), "Except"),
    (re.compile(r"\bAs well as\b", re.I), "and"),
    (re.compile(r"\bIn terms of\b", re.I), "In"),
    (re.compile(r"\bA large number of\b", re.I), "Many"),
    (re.compile(r"\bA significant number of\b", re.I), "Many"),
    (re.compile(r"\bThe vast majority of\b", re.I), "Most"),
    (re.compile(r"\bEach and every\b", re.I), "Every"),
    (re.compile(r"\bFirst and foremost\b", re.I), "First"),
    (re.compile(r"\bthe best practices for\b", re.I), "best practices for"),
    (re.compile(r"\bhow to properly\b", re.I), "how to"),
    (re.compile(r"\bhow to correctly\b", re.I), "how to"),
    (re.compile(r"\bhow to effectively\b", re.I), "how to"),
]

# --- German (DE) Verbose Patterns ---
VERBOSE_PATTERNS_DE: list[tuple[re.Pattern, str]] = [
    # Polite fluff
    (re.compile(r"\bbitte\s+", re.I), ""),
    (re.compile(r"\bIch möchte,? dass (?:du|Sie)\s+", re.I), ""),
    (re.compile(r"\bIch hätte gerne,? dass (?:du|Sie)\s+", re.I), ""),
    (re.compile(r"\bIch würde gerne wissen\s+", re.I), "Erkläre "),
    (re.compile(r"\bKönnten Sie bitte\s+", re.I), ""),
    (re.compile(r"\bKönntest du bitte\s+", re.I), ""),
    (re.compile(r"\bWürden Sie bitte\s+", re.I), ""),
    (re.compile(r"\bWürdest du bitte\s+", re.I), ""),
    (re.compile(r"\bIch brauche,? dass (?:du|Sie)\s+", re.I), ""),
    (re.compile(r"\bIch würde mich freuen,? wenn (?:du|Sie)\s+", re.I), ""),
    (re.compile(r"\bEs wäre schön,? wenn (?:du|Sie)\s+", re.I), ""),
    (re.compile(r"\bEs wäre toll,? wenn (?:du|Sie)\s+", re.I), ""),
    (re.compile(r"\bKannst du auch\s+", re.I), "Auch "),
    (re.compile(r"\bKönnen Sie auch\s+", re.I), "Auch "),
    (re.compile(r"\bHilf mir zu verstehen\s+", re.I), "Erkläre "),
    (re.compile(r"\bIch frage mich,? ob (?:du|Sie)\s+", re.I), ""),
    (re.compile(r"\bIch bin auf der Suche nach\s+", re.I), "Finde "),
    (re.compile(r"\bIch suche nach\s+", re.I), "Finde "),
    # "Ich möchte, dass du mir bitte erklärst" — more polite forms
    (re.compile(r"\bIch möchte,? dass du mir (?:bitte )?erklärst\s*,?\s*", re.I), "Erkläre "),
    (re.compile(r"\bKönnten Sie (?:bitte )?(?:auch )?(?:mir )?erklären\s*,?\s*", re.I), "Erkläre "),
    (re.compile(r"\b[Ww]äre es toll,? wenn du es\s+", re.I), ""),
    (re.compile(r"\b[Ww]enn du es\s+", re.I), ""),
    # Wordy connectors
    (re.compile(r"\bAufgrund der Tatsache,? dass\b", re.I), "Weil"),
    (re.compile(r"\bZum jetzigen Zeitpunkt\b", re.I), "Jetzt"),
    (re.compile(r"\bIm Hinblick auf\b", re.I), "Über"),
    (re.compile(r"\bIn Bezug auf\b", re.I), "Über"),
    (re.compile(r"\bMit Bezug auf\b", re.I), "Über"),
    (re.compile(r"\bDarüber hinaus\b", re.I), "Auch"),
    (re.compile(r"\bDes Weiteren\b", re.I), "Auch"),
    (re.compile(r"\bAus diesem Grund\b", re.I), "Deshalb"),
    (re.compile(r"\bUnter Berücksichtigung\b", re.I), "Beachte"),
    (re.compile(r"\bMit Ausnahme von\b", re.I), "Außer"),
    (re.compile(r"\bEine große Anzahl von\b", re.I), "Viele"),
    (re.compile(r"\bDie große Mehrheit\b", re.I), "Die meisten"),
    (re.compile(r"\bIn erster Linie\b", re.I), "Erstens"),
    (re.compile(r"\bZuallererst\b", re.I), "Erstens"),
]

# --- Spanish (ES) Verbose Patterns ---
VERBOSE_PATTERNS_ES: list[tuple[re.Pattern, str]] = [
    # Polite fluff
    (re.compile(r"\bpor favor\s+", re.I), ""),
    (re.compile(r"\bMe gustaría que\s+", re.I), ""),
    (re.compile(r"\bQuiero que\s+", re.I), ""),
    (re.compile(r"\bNecesito que\s+", re.I), ""),
    (re.compile(r"\bPodrías por favor\s+", re.I), ""),
    (re.compile(r"\bPuedes por favor\s+", re.I), ""),
    (re.compile(r"\b¿?Podrías\s+", re.I), ""),
    (re.compile(r"\b¿?Puedes\s+", re.I), ""),
    (re.compile(r"\b¿?Sería posible\s+", re.I), ""),
    (re.compile(r"\bTe agradecería que\s+", re.I), ""),
    (re.compile(r"\bMe encantaría que\s+", re.I), ""),
    (re.compile(r"\bSería genial si pudieras\s+", re.I), ""),
    (re.compile(r"\bEs importante que\s+", re.I), ""),
    (re.compile(r"\bAsegúrate de\s+", re.I), ""),
    (re.compile(r"\bEstoy buscando\s+", re.I), "Encuentra "),
    (re.compile(r"\bMe interesa\s+", re.I), "Incluye "),
    (re.compile(r"\bMe preguntaba si podrías\s+", re.I), ""),
    (re.compile(r"\bAyúdame a entender\s+", re.I), "Explica "),
    (re.compile(r"\b¿?Crees que podrías\s+", re.I), ""),
    # Wordy connectors
    (re.compile(r"\bCon el fin de\b", re.I), "Para"),
    (re.compile(r"\bCon el objetivo de\b", re.I), "Para"),
    (re.compile(r"\bDebido al hecho de que\b", re.I), "Porque"),
    (re.compile(r"\bDebido a que\b", re.I), "Porque"),
    (re.compile(r"\bEn este momento\b", re.I), "Ahora"),
    (re.compile(r"\bEn el caso de que\b", re.I), "Si"),
    (re.compile(r"\bCon respecto a\b", re.I), "Sobre"),
    (re.compile(r"\bEn relación con\b", re.I), "Sobre"),
    (re.compile(r"\bCon la finalidad de\b", re.I), "Para"),
    (re.compile(r"\bAdemás de eso\b", re.I), "También"),
    (re.compile(r"\bAdemás de\b", re.I), "También"),
    (re.compile(r"\bComo resultado de\b", re.I), "Por"),
    (re.compile(r"\bPor otro lado\b", re.I), "Sin embargo"),
    (re.compile(r"\bA pesar del hecho de que\b", re.I), "A pesar de"),
    (re.compile(r"\bTeniendo en cuenta\b", re.I), "Considerando"),
    (re.compile(r"\bEn el contexto de\b", re.I), "En"),
    (re.compile(r"\bCon la excepción de\b", re.I), "Excepto"),
    (re.compile(r"\bUn gran número de\b", re.I), "Muchos"),
    (re.compile(r"\bLa gran mayoría de\b", re.I), "La mayoría de"),
    (re.compile(r"\bEn primer lugar\b", re.I), "Primero"),
    (re.compile(r"\bAnte todo\b", re.I), "Primero"),
]

# --- French (FR) Verbose Patterns ---
VERBOSE_PATTERNS_FR: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bs'il vous plaît\s*,?\s*", re.I), ""),
    (re.compile(r"\bs'il te plaît\s*,?\s*", re.I), ""),
    (re.compile(r"\bJe voudrais que vous\s+", re.I), ""),
    (re.compile(r"\bJe voudrais que tu\s+", re.I), ""),
    (re.compile(r"\bJ'aimerais que vous\s+", re.I), ""),
    (re.compile(r"\bJ'aimerais que tu\s+", re.I), ""),
    (re.compile(r"\bPourriez-vous\s+", re.I), ""),
    (re.compile(r"\bPourrais-tu\s+", re.I), ""),
    (re.compile(r"\bPeut-on\s+", re.I), ""),
    (re.compile(r"\bJ'ai besoin que vous\s+", re.I), ""),
    (re.compile(r"\bJe vous serais reconnaissant si vous pouviez\s+", re.I), ""),
    (re.compile(r"\bCe serait bien si vous pouviez\s+", re.I), ""),
    (re.compile(r"\bCe serait super si tu pouvais\s+", re.I), ""),
    (re.compile(r"\bIl est important que vous\s+", re.I), ""),
    (re.compile(r"\bAssurez-vous de\s+", re.I), ""),
    (re.compile(r"\bAssure-toi de\s+", re.I), ""),
    (re.compile(r"\bVeuillez\s+", re.I), ""),
    (re.compile(r"\bJe cherche\s+", re.I), "Trouve "),
    (re.compile(r"\bJe suis intéressé par\s+", re.I), "Inclus "),
    (re.compile(r"\bJe me demandais si vous pouviez\s+", re.I), ""),
    (re.compile(r"\bAidez-moi à comprendre\s+", re.I), "Expliquez "),
    (re.compile(r"\bAide-moi à comprendre\s+", re.I), "Explique "),
    # Wordy connectors
    (re.compile(r"\bAfin de\b", re.I), "Pour"),
    (re.compile(r"\bEn raison du fait que\b", re.I), "Parce que"),
    (re.compile(r"\bÀ ce stade\b", re.I), "Maintenant"),
    (re.compile(r"\bEn ce qui concerne\b", re.I), "Sur"),
    (re.compile(r"\bPar rapport à\b", re.I), "Sur"),
    (re.compile(r"\bDans le but de\b", re.I), "Pour"),
    (re.compile(r"\bEn plus de cela\b", re.I), "Aussi"),
    (re.compile(r"\bEn plus de\b", re.I), "Aussi"),
    (re.compile(r"\bD'autre part\b", re.I), "Cependant"),
    (re.compile(r"\bMalgré le fait que\b", re.I), "Malgré"),
    (re.compile(r"\bEn tenant compte de\b", re.I), "Considérant"),
    (re.compile(r"\bDans le contexte de\b", re.I), "Dans"),
    (re.compile(r"\bÀ l'exception de\b", re.I), "Sauf"),
    (re.compile(r"\bUn grand nombre de\b", re.I), "Beaucoup de"),
    (re.compile(r"\bLa grande majorité de\b", re.I), "La plupart de"),
    (re.compile(r"\bTout d'abord\b", re.I), "D'abord"),
    (re.compile(r"\bEn premier lieu\b", re.I), "D'abord"),
]

# --- Italian (IT) Verbose Patterns ---
VERBOSE_PATTERNS_IT: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bper favore\s*,?\s*", re.I), ""),
    (re.compile(r"\bper piacere\s*,?\s*", re.I), ""),
    (re.compile(r"\bVorrei che (?:tu|lei)\s+", re.I), ""),
    (re.compile(r"\bMi piacerebbe che (?:tu|lei)\s+", re.I), ""),
    (re.compile(r"\bHo bisogno che (?:tu|lei)\s+", re.I), ""),
    (re.compile(r"\bPotresti\s+", re.I), ""),
    (re.compile(r"\bPotrebbe\s+", re.I), ""),
    (re.compile(r"\bSarebbe possibile\s+", re.I), ""),
    (re.compile(r"\bTi sarei grato se potessi\s+", re.I), ""),
    (re.compile(r"\bSarebbe bello se potessi\s+", re.I), ""),
    (re.compile(r"\bÈ importante che (?:tu|lei)\s+", re.I), ""),
    (re.compile(r"\bAssicurati di\s+", re.I), ""),
    (re.compile(r"\bDovresti sempre\s+", re.I), ""),
    (re.compile(r"\bSto cercando\s+", re.I), "Trova "),
    (re.compile(r"\bMi interessa\s+", re.I), "Includi "),
    (re.compile(r"\bMi chiedevo se potessi\s+", re.I), ""),
    (re.compile(r"\bAiutami a capire\s+", re.I), "Spiega "),
    # Wordy connectors
    (re.compile(r"\bAl fine di\b", re.I), "Per"),
    (re.compile(r"\bA causa del fatto che\b", re.I), "Perché"),
    (re.compile(r"\bIn questo momento\b", re.I), "Ora"),
    (re.compile(r"\bPer quanto riguarda\b", re.I), "Su"),
    (re.compile(r"\bIn relazione a\b", re.I), "Su"),
    (re.compile(r"\bCon lo scopo di\b", re.I), "Per"),
    (re.compile(r"\bOltre a ciò\b", re.I), "Anche"),
    (re.compile(r"\bOltre a\b", re.I), "Anche"),
    (re.compile(r"\bD'altra parte\b", re.I), "Tuttavia"),
    (re.compile(r"\bNonostante il fatto che\b", re.I), "Nonostante"),
    (re.compile(r"\bTenendo conto di\b", re.I), "Considerando"),
    (re.compile(r"\bNel contesto di\b", re.I), "In"),
    (re.compile(r"\bCon l'eccezione di\b", re.I), "Tranne"),
    (re.compile(r"\bUn gran numero di\b", re.I), "Molti"),
    (re.compile(r"\bLa grande maggioranza di\b", re.I), "La maggior parte di"),
    (re.compile(r"\bInnanzitutto\b", re.I), "Prima"),
    (re.compile(r"\bPrima di tutto\b", re.I), "Prima"),
]

# --- Turkish (TR) Verbose Patterns ---
VERBOSE_PATTERNS_TR: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\blütfen\s+", re.I), ""),
    (re.compile(r"\bRica etsem\s*,?\s*", re.I), ""),
    (re.compile(r"\b(?:Bana |bana )?yardım (?:eder misin|eder misiniz|et)\s*[?.]?\s*", re.I), ""),
    (re.compile(r"\b\.{3}(?:yapmanızı|yapmanı) istiyorum\.?\s*", re.I), ""),
    (re.compile(r"\b\.{3}(?:yapabilir misiniz|yapabilir misin)\s*\??\s*", re.I), ""),
    (re.compile(r"\bAcaba\s+", re.I), ""),
    (re.compile(r"\bMümkünse\s*,?\s*", re.I), ""),
    (re.compile(r"\bEğer mümkünse\s*,?\s*", re.I), ""),
    (re.compile(r"\bZahmet olmazsa\s*,?\s*", re.I), ""),
    (re.compile(r"\bAnlamamda yardımcı ol(?:ur musun|ur musunuz)?\s*", re.I), "Açıkla "),
    (re.compile(r"\bArıyorum\s+", re.I), "Bul "),
    (re.compile(r"\b(?:İlgileniyorum|ilgileniyorum)\s+", re.I), "Dahil et "),
    (re.compile(r"\bMerak ediyorum\s*,?\s*", re.I), ""),
    # "açıklar mısın" / "açıklayabilir misin" polite question forms
    (re.compile(r"\baçıklar mısın\b", re.I), "açıkla"),
    (re.compile(r"\baçıklayabilir misin\b", re.I), "açıkla"),
    (re.compile(r"\baçıklayabilir misiniz\b", re.I), "açıklayın"),
    (re.compile(r"\bönerilerde bulunabilir misin\b", re.I), "öner"),
    # Wordy connectors — use looser boundaries for agglutinative Turkish
    (re.compile(r"\b(?:Bunun|bunun) sebebi(?:yle| olarak)\b", re.I), "Çünkü"),
    (re.compile(r"\bŞu anda\b", re.I), "Şimdi"),
    (re.compile(r"\bBu noktada\b", re.I), "Şimdi"),
    # "...le/la/yle/yla ilgili olarak" — suffix-attached in Turkish
    (re.compile(r"(?:le|la|yle|yla) ilgili olarak", re.I), " hakkında"),
    # Also catch standalone form
    (re.compile(r"\bile ilgili olarak\b", re.I), "hakkında"),
    (re.compile(r"\bBuna ek olarak\b", re.I), "Ayrıca"),
    (re.compile(r"\bBunun yanı sıra\b", re.I), "Ayrıca"),
    (re.compile(r"\bÖte yandan\b", re.I), "Ancak"),
    (re.compile(r"\bBuna rağmen\b", re.I), "Rağmen"),
    # "göz önünde bulundurarak" — also handle "göz önüne alarak"
    (re.compile(r"göz önünde bulundurarak", re.I), "dikkate alarak"),
    (re.compile(r"göz önüne alarak", re.I), "dikkate alarak"),
    (re.compile(r"\bBağlamında\b", re.I), "İçinde"),
    (re.compile(r"\bHariç olmak üzere\b", re.I), "Hariç"),
    (re.compile(r"\bÇok sayıda\b", re.I), "Birçok"),
    (re.compile(r"\bBüyük çoğunluk\b", re.I), "Çoğu"),
    (re.compile(r"\bHer şeyden önce\b", re.I), "Önce"),
    (re.compile(r"\bİlk olarak\b", re.I), "Önce"),
    # NEW: More Turkish wordy phrases
    (re.compile(r"\bamacıyla\b", re.I), "için"),
    (re.compile(r"\bamacı doğrultusunda\b", re.I), "için"),
    (re.compile(r"gerçeğinden dolayı", re.I), "nedeniyle"),
    (re.compile(r"olduğu gerçeğinden", re.I), "olduğundan"),
    (re.compile(r"\bsöz konusu olduğu\b", re.I), "olan"),
    (re.compile(r"\bmevcut durumu anlamak\b", re.I), "durumu anlamak"),
    (re.compile(r"\b(?:bir )?analiz yapmanı istiyorum\b", re.I), "analiz yap"),
    (re.compile(r"\bhakkında bir analiz yap\b", re.I), "analiz et"),
    (re.compile(r"\bkonusunda\b", re.I), "hakkında"),
]

# --- Language-specific pattern lookup ---
FILLER_BY_LANG: dict[str, list[tuple[re.Pattern, str]]] = {
    "en": FILLER_PATTERNS,
    "de": FILLER_PATTERNS_DE,
    "es": FILLER_PATTERNS_ES,
    "fr": FILLER_PATTERNS_FR,
    "it": FILLER_PATTERNS_IT,
    "tr": FILLER_PATTERNS_TR,
}

VERBOSE_BY_LANG: dict[str, list[tuple[re.Pattern, str]]] = {
    "en": VERBOSE_PATTERNS,
    "de": VERBOSE_PATTERNS_DE,
    "es": VERBOSE_PATTERNS_ES,
    "fr": VERBOSE_PATTERNS_FR,
    "it": VERBOSE_PATTERNS_IT,
    "tr": VERBOSE_PATTERNS_TR,
}

# Redundant instruction patterns (often repeated in system prompts)
# Expanded to catch more variations
REDUNDANT_INSTRUCTIONS = [
    # "You are a helpful assistant" variations
    re.compile(r"You are an? (?:very )?(?:helpful|knowledgeable|friendly|professional)(?: and (?:helpful|knowledgeable|friendly|professional))* (?:AI )?assistant\.?\s*", re.I),
    # "You should be helpful/accurate" variations
    re.compile(r"You should (?:always )?(?:be|try to be) (?:helpful|accurate|concise|clear|thorough)(?: and (?:helpful|accurate|concise|clear|thorough))*\.?\s*", re.I),
    # "Provide helpful answers" variations
    re.compile(r"(?:Always )?(?:provide|give|offer) (?:helpful|useful|accurate|detailed|comprehensive) (?:and (?:helpful|useful|accurate|detailed|comprehensive) )?(?:answers|responses|information|explanations)\.?\s*", re.I),
    # "Explain things clearly" variations
    re.compile(r"(?:Try to |Make sure to )?(?:explain|describe) (?:things |everything )?(?:clearly|thoroughly|in detail)(?: and (?:clearly|thoroughly|in detail))*\.?\s*", re.I),
    # "Be as helpful as possible"
    re.compile(r"(?:Be|Try to be) as (?:helpful|clear|concise|accurate) as (?:possible|you can)\.?\s*", re.I),
    # "Your goal is to help"
    re.compile(r"Your (?:goal|purpose|job|role) is to (?:help|assist|support) (?:the )?user[s]?\.?\s*", re.I),
    # "You are designed to help"
    re.compile(r"You are designed to (?:help|assist|be helpful)\.?\s*", re.I),
    # "Respond in a helpful manner"
    re.compile(r"Respond in a (?:helpful|friendly|professional|clear) (?:and (?:helpful|friendly|professional|clear) )?(?:manner|way|tone)\.?\s*", re.I),

    # --- NEW: More redundant patterns ---
    # "Do not generate harmful content" / safety boilerplate
    re.compile(r"(?:Do not|Never|Don't) (?:generate|produce|create|output|write) (?:harmful|offensive|inappropriate|dangerous) (?:content|material|text|responses?)\.?\s*", re.I),
    re.compile(r"(?:Always )?(?:be|remain) (?:respectful|polite|professional|courteous)\.?\s*", re.I),
    re.compile(r"(?:Do not|Never) (?:engage in|discuss) (?:inappropriate|harmful|offensive) (?:topics|subjects|content)\.?\s*", re.I),
    re.compile(r"(?:Always )?prioritize (?:safety|user safety|helpfulness)\.?\s*", re.I),
    re.compile(r"(?:Never|Do not) produce (?:offensive|harmful|inappropriate) content\.?\s*", re.I),
    re.compile(r"(?:Make sure|Ensure) (?:your )?(?:responses?|answers?) (?:are|is) (?:family[- ]friendly|safe|appropriate)\.?\s*", re.I),
    # "Be concise/brief" repetitions
    re.compile(r"(?:Keep|Make) (?:your )?(?:answers?|responses?|it) (?:short|brief|concise)(?:\s+and\s+(?:short|brief|concise|to the point))?\.?\s*", re.I),
    re.compile(r"(?:Do not|Don't|Avoid) (?:write|writing|include|including) (?:long|lengthy|unnecessary) (?:paragraphs?|explanations?|details?)\.?\s*", re.I),
    re.compile(r"(?:Keep it|Be) (?:short|brief|concise) and (?:to the point|simple)\.?\s*", re.I),
    re.compile(r"Avoid (?:unnecessary|extra|excessive) (?:details?|information|words?|verbosity)\.?\s*", re.I),
    # "Format your response" boilerplate
    re.compile(r"(?:Always )?(?:format|structure) (?:your )?(?:output|response|answer)s? (?:nicely|properly|well)\.?\s*", re.I),
    re.compile(r"(?:Use|Always use) (?:proper|correct|appropriate) (?:markdown )?formatting(?: throughout)?\.?\s*", re.I),
    # "You have deep knowledge" / credential padding
    re.compile(r"You (?:have|possess) (?:deep|extensive|broad|comprehensive) (?:knowledge|expertise|understanding) (?:of|in|about) .{5,60}\.?\s*", re.I),
    re.compile(r"You (?:understand|know about) .{5,40}\.?\s*", re.I),
    re.compile(r"You are (?:highly )?(?:experienced|skilled|proficient) (?:in|at|with) .{5,60}\.?\s*", re.I),
    re.compile(r"Your expertise covers .{5,60}\.?\s*", re.I),
]

# --- German (DE) Redundant Instructions ---
REDUNDANT_INSTRUCTIONS_DE = [
    # "Du bist ein sehr hilfreicher, sachkundiger und freundlicher KI-Assistent"
    # Handle comma-separated adjectives and KI-Assistent
    re.compile(r"Du bist ein(?:e)? (?:sehr )?(?:hilfreiche[rs]?|freundliche[rs]?|professionelle[rs]?|sachkundige[rs]?|kompetente[rs]?)(?:,? (?:und )?(?:hilfreiche[rs]?|freundliche[rs]?|professionelle[rs]?|sachkundige[rs]?|kompetente[rs]?))* (?:KI-)?Assistent(?:in)?\.?\s*", re.I),
    # "Du solltest immer versuchen, hilfreich und genau zu sein"
    re.compile(r"Du solltest (?:immer )?(?:versuchen,? )?(?:höflich|freundlich|professionell|klar|genau|hilfreich)(?: und (?:höflich|freundlich|professionell|klar|genau|hilfreich))* (?:zu )?(?:sein|antworten|reagieren)\.?\s*", re.I),
    re.compile(r"(?:Bitte )?(?:gib|antworte|reagiere) (?:immer )?(?:klar|präzise|genau|höflich|freundlich|ausführlich)\w*(?: und (?:klar|präzise|genau|höflich|freundlich|ausführlich|umfassend)\w*)*(?: Antworten)?(?: auf alle Fragen)?\.?\s*", re.I),
    re.compile(r"(?:Gib|Liefere|Biete) (?:hilfreiche|nützliche|genaue|detaillierte|umfassende|ausführliche)\w*(?: und (?:hilfreiche|nützliche|genaue|detaillierte|umfassende|ausführliche)\w*)? (?:Antworten|Informationen|Erklärungen)(?: auf alle Fragen)?\.?\s*", re.I),
    # "Stelle sicher, dass du die Dinge klar und gründlich erklärst"
    re.compile(r"(?:Stelle sicher|Achte darauf),? dass du (?:die )?(?:Dinge|alles) (?:klar|deutlich|gründlich|ausführlich|verständlich)(?: und (?:klar|deutlich|gründlich|ausführlich|verständlich))* (?:erklärst|beschreibst)\.?\s*", re.I),
    re.compile(r"(?:Sei|Versuche) so (?:hilfreich|klar|genau|präzise) wie möglich\.?\s*", re.I),
    re.compile(r"Deine? (?:Aufgabe|Ziel|Rolle) ist es,? (?:dem Benutzer |den Benutzern )?(?:zu helfen|zu unterstützen)\.?\s*", re.I),
    re.compile(r"Du hast (?:umfassendes|tiefes|breites) (?:Wissen|Kenntnisse|Verständnis) (?:über|in|von) .{5,60}\.?\s*", re.I),
    re.compile(r"(?:Stelle sicher|Achte darauf),? dass (?:deine )?(?:Antworten|Reaktionen) (?:angemessen|sicher|familienfreundlich) (?:sind|bleiben)\.?\s*", re.I),
    re.compile(r"(?:Vermeide|Generiere keine) (?:schädliche|unangemessene|offensive) (?:Inhalte|Antworten)\.?\s*", re.I),
    # JSON/format repetition
    re.compile(r"(?:Stelle sicher|Sorge dafür),? dass (?:deine )?(?:Antwort|Ausgabe) (?:gültiges|korrektes|korrekt formatiertes) JSON ist\.?\s*", re.I),
    re.compile(r"Die (?:Antwort|Ausgabe) (?:muss|soll|sollte) im JSON-?(?:Format)? sein\.?\s*", re.I),
    re.compile(r"(?:Füge|Schreibe) nichts (?:außerhalb|neben) der JSON-?(?:Struktur)? (?:hinzu|ein)\.?\s*", re.I),
    re.compile(r"(?:Antworte|Reagiere) (?:immer )?im JSON-?(?:Format)?\.?\s*", re.I),
    # App chatbot patterns
    re.compile(r"(?:Stelle sicher|Achte darauf),? dass du (?:geduldig|verständnisvoll)(?: und (?:geduldig|verständnisvoll))* bist\.?\s*", re.I),
    re.compile(r"(?:Versuche|Bemühe dich) (?:immer)?,? das Problem (?:beim|im) ersten (?:Kontakt|Interaktion) zu (?:lösen|beheben)\.?\s*", re.I),
    re.compile(r"Wenn du etwas nicht weißt,? lass den Kunden (?:bitte )?wissen,? dass du das Problem weiterleiten wirst\.?\s*", re.I),
]

# --- Spanish (ES) Redundant Instructions ---
REDUNDANT_INSTRUCTIONS_ES = [
    # "Eres un asistente de IA muy útil" — adj after noun in Spanish
    re.compile(r"Eres un(?:a)? (?:asistente|IA)(?: de IA)? (?:muy )?(?:útil|amable|profesional|servicial|conocedor|amigable)(?: y (?:útil|amable|profesional|servicial|conocedor|amigable))*\.?\s*", re.I),
    # Also handle adj-before-noun variant
    re.compile(r"Eres un(?:a)? (?:muy )?(?:útil|amable|profesional|servicial)(?: y (?:útil|amable|profesional|servicial))* asistente\.?\s*", re.I),
    re.compile(r"(?:Siempre )?(?:debes|tienes que) (?:responder|ser|intentar ser) (?:de manera )?(?:clara|precisa|útil|profesional)(?: y (?:clara|precisa|útil|profesional))*\.?\s*", re.I),
    re.compile(r"(?:Proporciona|Da|Ofrece) (?:respuestas|información|explicaciones) (?:útiles|detalladas|precisas|claras|completas)(?: y (?:útiles|detalladas|precisas|claras|completas))?(?: a todas las preguntas)?\.?\s*", re.I),
    # "Asegúrate de explicar las cosas de manera clara"
    re.compile(r"Asegúrate de (?:explicar|describir) (?:las cosas|todo) (?:de manera )?(?:clara|precisa|exhaustiva)(?: y (?:clara|precisa|exhaustiva))*\.?\s*", re.I),
    re.compile(r"Asegúrate de que (?:tus )?(?:respuestas|explicaciones) (?:sean|son) (?:apropiadas|seguras|claras|precisas)\.?\s*", re.I),
    re.compile(r"Asegúrate de (?:ser )?(?:paciente|comprensivo)(?: y (?:paciente|comprensivo))*\.?\s*", re.I),
    re.compile(r"(?:Sé|Intenta ser) lo más (?:útil|claro|preciso) posible\.?\s*", re.I),
    re.compile(r"Tu (?:objetivo|propósito|rol|función) es (?:ayudar|asistir|apoyar) (?:al )?(?:usuario|los usuarios)\.?\s*", re.I),
    re.compile(r"Tienes (?:amplio|profundo|extenso) (?:conocimiento|experiencia) (?:en|sobre|de) .{5,60}\.?\s*", re.I),
    re.compile(r"(?:Nunca|No) (?:generes|produzcas|crees) (?:contenido|material|texto) (?:dañino|ofensivo|inapropiado)\.?\s*", re.I),
    re.compile(r"(?:Siempre )?(?:sé|mantente) (?:respetuoso|cortés|profesional)\.?\s*", re.I),
    # JSON/format repetition
    re.compile(r"(?:Asegúrate|Garantiza|Verifica) (?:de )?que (?:tu )?(?:respuesta|salida) (?:sea|es) (?:JSON )?(?:válido|correctamente formateado|JSON válido)\.?\s*", re.I),
    re.compile(r"La (?:respuesta|salida) (?:debe|debería) (?:estar )?en (?:formato )?JSON\.?\s*", re.I),
    re.compile(r"No (?:incluyas|agregues) nada (?:fuera|afuera) de la estructura JSON\.?\s*", re.I),
    re.compile(r"(?:Siempre )?(?:responde|responda) en (?:formato )?JSON\.?\s*", re.I),
    # App chatbot patterns
    re.compile(r"(?:Siempre )?(?:intenta|trata de) resolver el problema en la primera (?:interacción|comunicación)\.?\s*", re.I),
    re.compile(r"Si no sabes algo,? (?:por favor )?(?:hazle|haz) saber al cliente que (?:escalarás|transferirás) su (?:problema|consulta)\.?\s*", re.I),
]

# --- French (FR) Redundant Instructions ---
REDUNDANT_INSTRUCTIONS_FR = [
    # "Tu es un assistant utile" — adj AFTER noun in French
    re.compile(r"(?:Tu es|Vous êtes) un(?:e)? (?:assistant(?:e)?|IA) (?:très )?(?:utile|aimable|professionnel(?:le)?|serviable|compétent(?:e)?|amical(?:e)?)(?: et (?:utile|aimable|professionnel(?:le)?|serviable|compétent(?:e)?|amical(?:e)?))*\.?\s*", re.I),
    # Also handle adj-before-noun variant
    re.compile(r"(?:Tu es|Vous êtes) un(?:e)? (?:très )?(?:utile|aimable|professionnel(?:le)?|serviable)(?: et (?:utile|aimable|professionnel(?:le)?|serviable))* (?:assistant(?:e)?|IA)\.?\s*", re.I),
    re.compile(r"(?:Tu dois|Vous devez) (?:toujours )?(?:répondre|être) (?:de manière )?(?:claire|précise|utile|professionnelle)(?: et (?:claire|précise|utile|professionnelle))*\.?\s*", re.I),
    re.compile(r"(?:Fournis|Fournissez|Donne|Donnez) (?:des )?(?:réponses|informations|explications) (?:utiles|détaillées|précises|claires)(?: et (?:utiles|détaillées|précises|claires))?\.?\s*", re.I),
    re.compile(r"(?:Assure-toi|Assurez-vous) que (?:tes|vos) (?:réponses|explications) (?:soient|sont) (?:appropriées|sûres|claires|précises)\.?\s*", re.I),
    re.compile(r"(?:Assure-toi|Assurez-vous) d(?:'être|e être) (?:patient|compréhensif|poli|serviable)(?: et (?:patient|compréhensif|poli|serviable))*\.?\s*", re.I),
    re.compile(r"(?:Sois|Soyez) aussi (?:utile|clair|précis) que possible\.?\s*", re.I),
    re.compile(r"(?:Ton|Votre) (?:objectif|but|rôle) est d(?:'|e )(?:aider|assister) (?:l')?(?:utilisateur|les utilisateurs)\.?\s*", re.I),
    re.compile(r"(?:Tu as|Vous avez) (?:une )?(?:connaissance|expertise) (?:approfondie|étendue|vaste) (?:de|en|sur) .{5,60}\.?\s*", re.I),
    re.compile(r"(?:Ne )?(?:génère|produise)(?:z)? (?:jamais )?(?:de )?(?:contenu|matériel) (?:nuisible|offensant|inapproprié)\.?\s*", re.I),
    # JSON/format repetition
    re.compile(r"(?:Assure-toi|Assurez-vous|Vérifie|Vérifiez) que (?:ta|votre|la) (?:réponse|sortie) (?:est|soit) (?:du )?JSON (?:valide|correctement formaté|bien formaté)\.?\s*", re.I),
    re.compile(r"La (?:réponse|sortie) (?:doit|devrait) être en (?:format )?JSON\.?\s*", re.I),
    re.compile(r"N(?:'inclus|'incluez) rien (?:en dehors|à l'extérieur) de la structure JSON\.?\s*", re.I),
    re.compile(r"(?:Réponds|Répondez) toujours en (?:format )?JSON\.?\s*", re.I),
    # "Essaie toujours de résoudre" / "Fais savoir au client"
    re.compile(r"(?:Essaie|Essayez) (?:toujours )?de (?:résoudre|régler) le problème (?:dès )?(?:la première|au premier) (?:interaction|contact)\.?\s*", re.I),
    re.compile(r"Si (?:tu|vous) ne (?:sais|savez) pas quelque chose,? (?:fais|faites) savoir au client que (?:tu vas|vous allez) (?:transférer|escalader) (?:son|le) problème\.?\s*", re.I),
]

# --- Italian (IT) Redundant Instructions ---
REDUNDANT_INSTRUCTIONS_IT = [
    # "Sei un assistente utile" — adj AFTER noun in Italian
    re.compile(r"(?:Sei|Tu sei) un(?:'|a)? (?:assistente|IA) (?:molto )?(?:utile|gentile|professionale|servizievole|competente|amichevole)(?: e (?:utile|gentile|professionale|servizievole|competente|amichevole))*\.?\s*", re.I),
    # Also handle adj-before-noun variant
    re.compile(r"(?:Sei|Tu sei) un(?:'|a)? (?:molto )?(?:utile|gentile|professionale|servizievole)(?: e (?:utile|gentile|professionale|servizievole))* assistente\.?\s*", re.I),
    re.compile(r"(?:Devi|Dovresti) (?:sempre )?(?:rispondere|essere) (?:in modo )?(?:chiaro|preciso|utile|professionale)(?: e (?:chiaro|preciso|utile|professionale))*\.?\s*", re.I),
    re.compile(r"(?:Fornisci|Dai|Offri) (?:risposte|informazioni|spiegazioni) (?:utili|dettagliate|precise|chiare)(?: e (?:utili|dettagliate|precise|chiare))?\.?\s*", re.I),
    re.compile(r"Assicurati che (?:le )?(?:tue )?(?:risposte|spiegazioni) (?:siano|sono) (?:appropriate|sicure|chiare|precise)\.?\s*", re.I),
    re.compile(r"Assicurati di essere (?:paziente|comprensivo|educato|disponibile)(?: e (?:paziente|comprensivo|educato|disponibile))*\.?\s*", re.I),
    re.compile(r"(?:Sii|Cerca di essere) il più (?:utile|chiaro|preciso) possibile\.?\s*", re.I),
    re.compile(r"Il tuo (?:obiettivo|scopo|ruolo) è (?:aiutare|assistere) (?:l')?(?:utente|gli utenti)\.?\s*", re.I),
    re.compile(r"(?:Hai|Possiedi) (?:una )?(?:conoscenza|competenza) (?:approfondita|vasta|ampia) (?:di|in|su) .{5,60}\.?\s*", re.I),
    re.compile(r"(?:Non )?(?:generare|produrre) (?:mai )?(?:contenuti?|materiale) (?:dannos[oi]|offensiv[oi]|inappropriat[oi])\.?\s*", re.I),
    # JSON/format repetition
    re.compile(r"(?:Assicurati|Verifica) che (?:la tua )?(?:risposta|l'output) (?:sia|è) (?:JSON )?(?:valido|correttamente formattato|JSON valido)\.?\s*", re.I),
    re.compile(r"La (?:risposta|output) (?:deve|dovrebbe) essere in (?:formato )?JSON\.?\s*", re.I),
    re.compile(r"Non (?:includere|aggiungere) nulla (?:al di fuori|fuori) della struttura JSON\.?\s*", re.I),
    re.compile(r"(?:Rispondi|Rispondete) sempre in (?:formato )?JSON\.?\s*", re.I),
    # App chatbot patterns
    re.compile(r"(?:Cerca|Prova) (?:sempre )?di risolvere il problema (?:al primo contatto|alla prima interazione)\.?\s*", re.I),
    re.compile(r"Se non (?:sai|conosci) qualcosa,? (?:fai|fa') sapere al cliente che (?:escalerai|trasferirai) (?:il suo )?problema\.?\s*", re.I),
]

# --- Turkish (TR) Redundant Instructions ---
REDUNDANT_INSTRUCTIONS_TR = [
    # "Sen yardımcı bir asistansın" — also handle "samimi", "bilgili" etc.
    re.compile(r"Sen (?:çok )?(?:yardımcı|kibar|profesyonel|bilgili|samimi)(?: ve (?:yardımcı|kibar|profesyonel|bilgili|samimi))* bir (?:yapay zeka )?(?:asistansın|asistanısın)\.?\s*", re.I),
    re.compile(r"(?:Her zaman )?(?:net|açık|yardımcı|profesyonel|doğru)(?: ve (?:net|açık|yardımcı|profesyonel|doğru))* (?:cevaplar ver|yanıtla|ol)\.?\s*", re.I),
    re.compile(r"(?:Yardımcı|Faydalı|Doğru|Detaylı|Kapsamlı|Ayrıntılı)(?: ve (?:yardımcı|faydalı|doğru|detaylı|kapsamlı|ayrıntılı))? (?:cevaplar|bilgiler|açıklamalar) (?:ver|sun|sağla)\.?\s*", re.I),
    re.compile(r"(?:Cevaplarının|Yanıtlarının) (?:uygun|güvenli|anlaşılır|doğru) (?:olduğundan|olmasından) emin ol\.?\s*", re.I),
    re.compile(r"(?:Mümkün olduğunca|Olabildiğince) (?:yardımcı|net|doğru|açık) ol\.?\s*", re.I),
    re.compile(r"(?:Amacın|Görevin|Rolün) (?:kullanıcıya|kullanıcılara) (?:yardım etmek|destek olmak)(?:tır|tir)?\.?\s*", re.I),
    re.compile(r"(?:Geniş|Derin|Kapsamlı) (?:bilgiye|uzmanlığa|deneyime) sahipsin .{5,60}\.?\s*", re.I),
    re.compile(r"(?:Asla|Hiçbir zaman) (?:zararlı|uygunsuz|saldırgan) (?:içerik|materyal|metin) (?:üretme|oluşturma)\.?\s*", re.I),
    # "Konuları açık ve detaylı bir şekilde açıkladığından emin ol"
    re.compile(r"(?:Konuları|Her şeyi) (?:açık|net|detaylı)(?: ve (?:açık|net|detaylı))*(?: bir şekilde)? (?:açıkladığından|anlattığından) emin ol\.?\s*", re.I),
    # JSON/format repetition
    re.compile(r"(?:Yanıtının|Cevabının|Çıktının) (?:geçerli |doğru (?:biçimlendirilmiş )?)?JSON (?:olduğundan|olduğunu|formatında olduğundan) (?:emin ol|kontrol et)\.?\s*", re.I),
    re.compile(r"(?:Yanıt|Cevap|Çıktı) JSON formatında (?:olmalıdır|olmalı|olsun)\.?\s*", re.I),
    re.compile(r"JSON (?:yapısının|formatının) dışında (?:hiçbir şey|bir şey) (?:ekleme|yazma)\.?\s*", re.I),
    re.compile(r"(?:Her zaman )?JSON formatında (?:yanıt ver|cevap ver|yanıtla)\.?\s*", re.I),
    # App chatbot patterns
    re.compile(r"(?:Her zaman )?(?:sorunu|problemi) ilk (?:iletişimde|kontakta) (?:çözmeye|halletmeye) çalış\.?\s*", re.I),
    re.compile(r"(?:Sabırlı|Anlayışlı)(?: ve (?:sabırlı|anlayışlı))* olduğundan emin ol\.?\s*", re.I),
    re.compile(r"Bir şeyi bilmiyorsan,? (?:müşteriye|kullanıcıya) (?:sorunun|problemin) (?:yönlendirileceğini|aktarılacağını) bildir\.?\s*", re.I),
]

# Language-specific redundant instruction lookup
REDUNDANT_BY_LANG: dict[str, list[re.Pattern]] = {
    "en": REDUNDANT_INSTRUCTIONS,
    "de": REDUNDANT_INSTRUCTIONS_DE,
    "es": REDUNDANT_INSTRUCTIONS_ES,
    "fr": REDUNDANT_INSTRUCTIONS_FR,
    "it": REDUNDANT_INSTRUCTIONS_IT,
    "tr": REDUNDANT_INSTRUCTIONS_TR,
}


def optimize_messages(
    messages: list[dict],
) -> tuple[list[dict], "InjectionResult | None"]:
    """
    Optimize a list of chat messages.
    Returns a tuple of (optimized messages, injection result or None).
    Does NOT mutate the original.

    Pipeline:
    0. Injection detection (always on, ~0.1ms)
    1. Rule-based optimization (~10-20% savings, <1ms)
    2. Conversation history truncation (basic)
    """
    if not settings.OPTIMIZER_ENABLED:
        return messages, None

    # --- STEP 0: Injection detection (before any optimization) ---
    injection_result = None
    if settings.INJECTION_ENABLED:
        injection_result = check_messages(messages)
        if injection_result.is_injection:
            messages = _sanitize_injected_messages(messages)
            print(f"[PITH:INJECTION] Detected: score={injection_result.score:.2f}, "
                  f"patterns={injection_result.matched_patterns}, layer={injection_result.layer}")

    # Detect language from ALL message content
    all_text = " ".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
    lang = _detect_language(all_text)

    optimized = []
    seen_system = set()
    seen_sentences = set()

    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")

        if not isinstance(content, str):
            optimized.append(msg)
            continue

        original_content = content

        # 1. System prompt deduplication
        if role == "system":
            content_hash = _normalize_for_hash(content)
            if content_hash in seen_system:
                continue
            seen_system.add(content_hash)

        # 2. Trim old assistant messages (basic truncation)
        #    For AI-powered Pith Distill compression, see pithtoken.ai
        if role == "assistant" and i < len(messages) - 4:
            if len(content) > 120:
                content = content[:100].rsplit(" ", 1)[0] + "..."

        # 3. Optimize content (with cache, language-aware)
        content = _optimize_text_cached(content, role, lang)

        # 4. Remove duplicate sentences across messages
        if role in ("system", "user"):
            content = _deduplicate_sentences(content, seen_sentences)

        # 5. Skip empty messages
        if not content.strip():
            continue

        # 6. Negative savings guard
        if len(content) > len(original_content):
            content = original_content

        optimized.append({**msg, "content": content})

    return optimized, injection_result
def _sanitize_injected_messages(messages: list[dict]) -> list[dict]:
    """Sanitize user messages that contain detected injection patterns."""
    sanitized = []
    for msg in messages:
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            clean_content = sanitize_prompt(msg["content"])
            sanitized.append({**msg, "content": clean_content})
        else:
            sanitized.append(msg)
    return sanitized


def _optimize_text_cached(text: str, role: str, lang: str = "en") -> str:
    """Check cache before optimizing."""
    key = _cache_key(text + role + lang)
    if key in _cache:
        return _cache[key]

    result = _optimize_text(text, role, lang)

    if len(_cache) < _CACHE_MAX:
        _cache[key] = result
    return result


def _optimize_text(text: str, role: str = "user", lang: str = "en") -> str:
    """Apply all optimization rules to a text string.
    Uses pre-detected language for language-specific patterns.
    """
    # Whitespace normalization
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^\s+$", "", text, flags=re.M)

    # Get language-specific patterns (fall back to English)
    filler_patterns = FILLER_BY_LANG.get(lang, FILLER_PATTERNS)
    verbose_patterns = VERBOSE_BY_LANG.get(lang, VERBOSE_PATTERNS)

    # PASS 1: Remove filler/hedge words FIRST (so verbose patterns match cleanly)
    for pattern, replacement in filler_patterns:
        text = pattern.sub(replacement, text)
    text = re.sub(r"  +", " ", text)  # Clean double spaces from removals

    # PASS 2: Verbose phrase replacement (now filler words are gone)
    for pattern, replacement in verbose_patterns:
        text = pattern.sub(replacement, text)

    # System-prompt-specific: remove redundant meta-instructions
    if role == "system":
        redundant_patterns = REDUNDANT_BY_LANG.get(lang, REDUNDANT_INSTRUCTIONS)
        for pattern in redundant_patterns:
            text = pattern.sub("", text)

    # Remove unnecessary markdown formatting (bold/italic used for emphasis in prompts)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)  # **bold** or *italic* -> plain
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)     # __bold__ or _italic_ -> plain

    # Remove list number/bullet redundancy in instructions
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.M)     # - item -> item
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.M)    # 1. item -> item

    # Clean up artifacts from replacements
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s*\.\s*$", "", text, flags=re.M)  # Orphan periods
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)         # Space before punctuation
    text = text.strip()

    # Capitalize first letter if it got lowercased
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    return text

def _deduplicate_sentences(text: str, seen: set) -> str:
    """Remove sentences that have already appeared."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    unique = []
    for s in sentences:
        normalized = re.sub(r"\s+", " ", s.lower().strip())
        if len(normalized) < 10:  # Keep short fragments
            unique.append(s)
            continue
        if normalized not in seen:
            seen.add(normalized)
            unique.append(s)
    return " ".join(unique)


def _normalize_for_hash(text: str) -> str:
    """Normalize text for deduplication comparison."""
    return re.sub(r"\s+", " ", text.lower().strip())


def estimate_savings(original: list[dict], optimized: list[dict]) -> dict:
    """Quick estimate without tiktoken (for logging)."""
    orig_chars = sum(len(m.get("content", "") or "") for m in original)
    opt_chars = sum(len(m.get("content", "") or "") for m in optimized)
    saved = orig_chars - opt_chars
    pct = (saved / orig_chars * 100) if orig_chars > 0 else 0
    return {
        "original_chars": orig_chars,
        "optimized_chars": opt_chars,
        "saved_percent": round(pct, 1),
    }
