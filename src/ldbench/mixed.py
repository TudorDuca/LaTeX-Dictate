"""Mixed speech -> prose with inline LaTeX, by splitting first and converting only the maths.

1. A segmenter LLM copies the transcript with every spoken-maths stretch wrapped in <m>...</m>.
2. Its tags are aligned back onto the *transcript's own words*: the prose in the output is always
   exactly what the speech recognizer heard. The segmenter only decides which words are maths;
   any words it dropped, added or changed are ignored.
3. Each maths span goes to an equation model (transcript -> LaTeX) and comes back as $...$.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Callable

from .postprocess import clean_output

SEGMENT_SYSTEM = (
    "You mark spoken mathematics in a speech transcript.\n"
    "Copy the transcript exactly, word for word, and wrap every stretch of words that describes a "
    "mathematical expression, formula, equation or variable in <m> and </m>. Do not add, remove or "
    "change any words, and do not convert anything to symbols.\n"
    "A single variable or number used mathematically counts as maths. Connecting words around a "
    "formula (so, then, we know that, where, for every, which means) are not maths."
)

# Hand-written examples (not from any test set).
SEGMENT_EXAMPLES = [
    ("so if f of x equals x squared then the derivative is two x",
     "so if <m>f of x equals x squared</m> then the derivative is <m>two x</m>"),
    ("assume p and q are coprime integers so p squared is even",
     "assume <m>p</m> and <m>q</m> are coprime integers so <m>p squared</m> is even"),
    ("I think the answer is wrong because the integral from zero to one of x dx is one half, not one",
     "I think the answer is wrong because <m>the integral from zero to one of x dx is one half</m>, not "
     "<m>one</m>"),
    ("can you explain why we need the chain rule here", "can you explain why we need the chain rule here"),
]

_EDGE_PUNCT = ".,;:!?\"'()"


def segment_messages(transcript: str) -> list[dict]:
    messages = [{"role": "system", "content": SEGMENT_SYSTEM}]
    for said, tagged in SEGMENT_EXAMPLES:
        messages += [{"role": "user", "content": said}, {"role": "assistant", "content": tagged}]
    messages.append({"role": "user", "content": transcript})
    return messages


def segment_max_tokens(transcript: str) -> int:
    return 48 + 4 * len(transcript.split())


def _norm(word: str) -> str:
    return re.sub(r"[^\w]", "", word.lower())


def parse_tagged(tagged: str) -> list[tuple[str, bool]]:
    """Words of the segmenter's reply, each with whether it sits inside <m>...</m>."""
    words: list[tuple[str, bool]] = []  # tags may touch words: "<m>x</m>," splits fine
    inside = False
    for piece in re.split(r"(</?m>)", tagged, flags=re.I):
        tag = piece.lower()
        if tag == "<m>":
            inside = True
        elif tag == "</m>":
            inside = False
        else:
            words += [(w, inside) for w in piece.split()]
    return words


def align_labels(transcript_words: list[str], tagged: list[tuple[str, bool]]) -> list[bool]:
    """Maths label per transcript word, copied from the segmenter's reply where the words align."""
    src = [_norm(w) for w in transcript_words]
    dst = [_norm(w) for w, _ in tagged]
    labels = [False] * len(src)
    matched = [False] * len(src)
    for block in SequenceMatcher(a=src, b=dst, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            labels[block.a + k] = tagged[block.b + k][1]
            matched[block.a + k] = True
    # A word the segmenter rewrote, sitting between two maths words, belongs to that formula.
    for i in range(1, len(src) - 1):
        if not matched[i] and labels[i - 1] and labels[i + 1]:
            labels[i] = True
    return labels


def spans(words: list[str], labels: list[bool]) -> list[tuple[bool, str, str, str]]:
    """Group words into (is_maths, leading punctuation, text, trailing punctuation) runs."""
    out: list[tuple[bool, str, str, str]] = []
    i = 0
    while i < len(words):
        j = i
        while j < len(words) and labels[j] == labels[i]:
            j += 1
        text = " ".join(words[i:j])
        if labels[i]:
            core = text.strip(_EDGE_PUNCT)
            lead = text[: len(text) - len(text.lstrip(_EDGE_PUNCT))]
            trail = text[len(text.rstrip(_EDGE_PUNCT)):]
            out.append((bool(core), lead, core or text, trail))
        else:
            out.append((False, "", text, ""))
        i = j
    return out


def convert_mixed(
    transcript: str,
    segment: Callable[[list[dict], int], str],
    convert_span: Callable[[str], str],
) -> dict:
    """Prose with $...$ maths. `segment` is an LLM call; `convert_span` maps spoken maths to LaTeX."""
    words = transcript.split()
    if not words:
        return {"text": "", "tagged": "", "spans": []}
    tagged = segment(segment_messages(transcript), segment_max_tokens(transcript))
    labels = align_labels(words, parse_tagged(tagged))
    parts, details = [], []
    for is_math, lead, text, trail in spans(words, labels):
        if not is_math:
            parts.append(text)
            continue
        latex = convert_span(text)
        details.append({"spoken": text, "latex": latex})
        # If conversion fails, keep the words: never lose what was said.
        parts.append(f"{lead}${latex}${trail}" if latex else f"{lead}{text}{trail}")
    return {"text": " ".join(parts), "tagged": tagged, "spans": details}


def span_converter(model, prompt_style: str, max_tokens_fn: Callable[[str], int]) -> Callable[[str], str]:
    """Equation model (transcript -> LaTeX) as a span converter."""
    from .prompts import text_messages

    def convert(spoken: str) -> str:
        raw = model.generate(text_messages(prompt_style, "equations", spoken), max_tokens_fn(spoken))
        return clean_output(raw, "equations")

    return convert
