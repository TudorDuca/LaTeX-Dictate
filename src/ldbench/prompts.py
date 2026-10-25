"""Prompts for the text step (transcript -> LaTeX) and for end-to-end audio models."""

from __future__ import annotations

ZERO_SHOT_SYSTEM = {
    "equations": (
        "You convert spoken mathematics into LaTeX.\n"
        "The input is an automatic speech-recognition transcript of someone saying one mathematical "
        "expression aloud. The transcript can contain recognition errors, such as words that sound like "
        'maths terms ("eggs" for "x", "pie" for "pi", "cosign" for "cosine"); interpret them as the '
        "intended mathematics.\n"
        "Reply with only the LaTeX for the expression: no $ delimiters, no explanation, no code fences."
    ),
    "sentences": (
        "You convert spoken mathematical text into LaTeX.\n"
        "The input is an automatic speech-recognition transcript of someone reading a sentence that "
        "contains mathematics. The transcript can contain recognition errors; fix them using context.\n"
        "Reply with only the sentence, keeping the ordinary words, and writing every mathematical "
        "expression as inline LaTeX between single dollar signs, e.g. $f(x)=x^{2}$. "
        "No explanation, no code fences."
    ),
}

ZERO_SHOT_USER = "Transcript: {transcript}"

# Exactly the format the paper's ASR post-correction models were fine-tuned on
# (speech2latex/ASRPostCorrection/dataset.py).
PAPER_SYSTEM = "You are a helpful assistant."
PAPER_USER = (
    "Please, give me LaTeX representation of the following formula. Formula pronunciation: {transcript}"
)

E2E_PROMPT = {
    "equations": (
        "The speaker says one mathematical expression aloud. Write that expression in LaTeX. "
        "Reply with only the LaTeX code: no $ delimiters, no explanation."
    ),
    "sentences": (
        "The speaker reads a sentence that contains mathematics. Write the sentence down, keeping the "
        "ordinary words and writing every mathematical expression as inline LaTeX between single "
        "dollar signs. Reply with only the sentence."
    ),
}


def text_messages(style: str, task: str, transcript: str) -> list[dict]:
    if style == "paper":
        return [
            {"role": "system", "content": PAPER_SYSTEM},
            {"role": "user", "content": PAPER_USER.format(transcript=transcript)},
        ]
    return [
        {"role": "system", "content": ZERO_SHOT_SYSTEM[task]},
        {"role": "user", "content": ZERO_SHOT_USER.format(transcript=transcript)},
    ]


def e2e_prompt(task: str) -> str:
    return E2E_PROMPT[task]
