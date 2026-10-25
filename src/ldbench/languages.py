"""Speech-language names: Whisper wants ISO codes ("es"), Qwen3-ASR wants names ("Spanish")."""

from __future__ import annotations

NAMES = {
    "en": "English", "es": "Spanish", "de": "German", "fr": "French", "it": "Italian", "pt": "Portuguese",
    "ru": "Russian", "zh": "Chinese", "yue": "Cantonese", "ja": "Japanese", "ko": "Korean", "nl": "Dutch",
    "ca": "Catalan", "pl": "Polish", "tr": "Turkish", "ar": "Arabic", "hi": "Hindi", "ro": "Romanian",
}
CODES = {name.lower(): code for code, name in NAMES.items()}


def to_code(language: str) -> str | None:
    """'es', 'ES', 'Spanish', 'spanish' -> 'es'; 'auto' -> None (detect)."""
    lang = language.strip().lower()
    if lang == "auto":
        return None
    if lang in NAMES:
        return lang
    if lang in CODES:
        return CODES[lang]
    raise ValueError(f"unknown language {language!r}; use a code like 'es' or a name like 'Spanish', or 'auto'")


def to_name(language: str) -> str | None:
    code = to_code(language)
    return None if code is None else NAMES[code]
