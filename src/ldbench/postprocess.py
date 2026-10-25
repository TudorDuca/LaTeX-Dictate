"""Turn raw model output into a bare LaTeX answer."""

from __future__ import annotations

import re

from .data import strip_math_delimiters

_THINK_RE = re.compile(r"<think>.*?</think>", re.S)
_FENCE_RE = re.compile(r"```(?:latex|tex|math)?\s*(.*?)```", re.S | re.I)
# "LaTeX:", "Latex -", "Answer:" ... at the start of the reply. The paper's models may also
# emit "Fixed transcribation: ...\nLaTex: ..." when trained with a transcription target.
_LABEL_RE = re.compile(r"^\s*(?:latex|output|answer|result)\s*[:\-]\s*", re.I)
_LAST_LATEX_LABEL_RE = re.compile(r"latex\s*:\s*", re.I)


def clean_output(raw: str, task: str) -> str:
    text = _THINK_RE.sub("", raw or "").strip()
    text = text.replace("<|endoftext|>", "").replace("<|im_end|>", "").strip()

    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()

    if "fixed transcribation" in text.lower():
        parts = _LAST_LATEX_LABEL_RE.split(text)
        text = parts[-1].strip()
    text = _LABEL_RE.sub("", text, count=1)

    text = " ".join(text.split())
    if task == "equations":
        text = strip_math_delimiters(text)
        # Drop sentence punctuation after the formula, but never the char of a "\," or "\;" command.
        while text and text[-1] in " .,;" and not text[:-1].endswith("\\"):
            text = text[:-1]
        text = strip_math_delimiters(text)
    return text
