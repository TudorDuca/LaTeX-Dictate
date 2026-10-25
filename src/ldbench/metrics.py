"""Metrics for spoken-maths -> LaTeX.

The headline metric is a corpus-level character error rate (CER) on *normalized* LaTeX, so that
notational variants that render identically (``x^2`` / ``x^{2}``, ``\\left(`` / ``(``, spacing
commands, ``\\dfrac`` / ``\\frac``) are not counted as errors.

This normalizer is deliberately lenient and is provisional for M0. Numbers comparable with the
Speech-to-LaTeX paper need the paper's own normalizer (planned for M1).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from rapidfuzz.distance import Levenshtein

from .data import strip_math_delimiters

_TOKEN_RE = re.compile(r"\\[A-Za-z]+|\\.|\S")

_SYNONYMS = {
    "\\dfrac": "\\frac",
    "\\tfrac": "\\frac",
    "\\le": "\\leq",
    "\\leqslant": "\\leq",
    "\\ge": "\\geq",
    "\\geqslant": "\\geq",
    "\\ne": "\\neq",
    "\\to": "\\rightarrow",
    "\\gets": "\\leftarrow",
    "\\lbrace": "\\{",
    "\\rbrace": "\\}",
    "\\lvert": "|",
    "\\rvert": "|",
    "\\vert": "|",
    "\\lVert": "\\|",
    "\\rVert": "\\|",
    "\\Vert": "\\|",
    "\\ldots": "\\dots",
    "\\cdots": "\\dots",
    "\\dotsc": "\\dots",
    "\\dotsb": "\\dots",
    "\\varepsilon": "\\epsilon",
    "\\varphi": "\\phi",
    "\\land": "\\wedge",
    "\\lor": "\\vee",
    "\\lnot": "\\neg",
    "\\iff": "\\Leftrightarrow",
    "\\implies": "\\Rightarrow",
    # The paper's normalized references drop escaped set braces; treat them as plain braces.
    "\\{": "{",
    "\\}": "}",
}

_DROP = {
    "\\left", "\\right", "\\bigl", "\\bigr", "\\Bigl", "\\Bigr", "\\biggl", "\\biggr",
    "\\big", "\\Big", "\\bigg", "\\Bigg", "\\displaystyle", "\\textstyle", "\\scriptstyle",
    "\\limits", "\\nolimits", "\\,", "\\;", "\\:", "\\!", "\\ ", "\\quad", "\\qquad", "~",
}


def latex_tokens(s: str) -> list[str]:
    """Normalized token sequence for one formula."""
    s = strip_math_delimiters(s or "")
    toks = [_SYNONYMS.get(t, t) for t in _TOKEN_RE.findall(s)]
    toks = [t for t in toks if t not in _DROP]
    # Remove braces around a single token everywhere: x^{2} -> x^2, \hat{\mu} -> \hat\mu.
    changed = True
    while changed:
        changed = False
        out: list[str] = []
        i = 0
        while i < len(toks):
            if (
                i + 2 < len(toks)
                and toks[i] == "{"
                and toks[i + 2] == "}"
                and toks[i + 1] not in ("{", "}")
            ):
                out.append(toks[i + 1])
                i += 3
                changed = True
            else:
                out.append(toks[i])
                i += 1
        toks = out
    return toks


def normalize_formula(s: str) -> str:
    return "".join(latex_tokens(s))


def split_inline_math(text: str) -> tuple[list[str], list[str]]:
    """(text parts, formula parts) of a sentence with $...$ inline maths."""
    parts = re.split(r"(?<!\\)\$\$?", text or "")
    return parts[0::2], parts[1::2]


def normalize_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return " ".join(s.split())


def normalize_sentence(text: str) -> str:
    texts, formulas = split_inline_math(text)
    out = []
    for i, t in enumerate(texts):
        out.append(normalize_text(t))
        if i < len(formulas):
            out.append("$" + normalize_formula(formulas[i]) + "$")
    return " ".join(p for p in out if p)


def sentence_formulas(text: str) -> str:
    return " ".join(normalize_formula(f) for f in split_inline_math(text)[1])


@dataclass
class ItemScore:
    edits: int
    ref_len: int
    tok_edits: int
    tok_len: int
    exact: bool


def score_item(pred: str, ref: str, task: str) -> dict[str, ItemScore]:
    """Scores per view: 'latex' for equations; 'full' and 'formulas' for sentences."""
    if task == "equations":
        return {"latex": _score_formula(pred, ref)}
    full_p, full_r = normalize_sentence(pred), normalize_sentence(ref)
    return {
        "full": ItemScore(
            Levenshtein.distance(full_p, full_r), len(full_r),
            Levenshtein.distance(full_p.split(), full_r.split()), len(full_r.split()),
            full_p == full_r,
        ),
        "formulas": _score_strings(sentence_formulas(pred), sentence_formulas(ref)),
    }


def _score_formula(pred: str, ref: str) -> ItemScore:
    pt, rt = latex_tokens(pred), latex_tokens(ref)
    p, r = "".join(pt), "".join(rt)
    return ItemScore(Levenshtein.distance(p, r), len(r), Levenshtein.distance(pt, rt), len(rt), pt == rt)


def _score_strings(p: str, r: str) -> ItemScore:
    pt, rt = p.split(), r.split()
    pc, rc = p.replace(" ", ""), r.replace(" ", "")
    return ItemScore(Levenshtein.distance(pc, rc), len(rc), Levenshtein.distance(pt, rt), len(rt), pc == rc)


def corpus_rates(scores: list[ItemScore]) -> dict[str, float]:
    ref = sum(s.ref_len for s in scores)
    tok = sum(s.tok_len for s in scores)
    return {
        "cer": sum(s.edits for s in scores) / ref if ref else float("nan"),
        "ter": sum(s.tok_edits for s in scores) / tok if tok else float("nan"),
        "exact": sum(s.exact for s in scores) / len(scores) if scores else float("nan"),
    }


def bootstrap_cer_ci(
    scores: list[ItemScore], n_boot: int = 1000, seed: int = 0, alpha: float = 0.05
) -> tuple[float, float]:
    """Percentile bootstrap CI for corpus CER, resampling items."""
    if not scores:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(scores)
    stats = []
    for _ in range(n_boot):
        sample = [scores[rng.randrange(n)] for _ in range(n)]
        ref = sum(s.ref_len for s in sample)
        stats.append(sum(s.edits for s in sample) / ref if ref else 0.0)
    stats.sort()
    lo = stats[int((alpha / 2) * n_boot)]
    hi = stats[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return lo, hi


def percentile(values: list[float], q: float) -> float:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return float("nan")
    k = (len(vals) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)
