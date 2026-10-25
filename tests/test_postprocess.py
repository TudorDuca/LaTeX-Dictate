import pytest

from ldbench.postprocess import clean_output


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("x^{2}", "x^{2}"),
        ("$x^{2}$", "x^{2}"),
        ("$$\\frac{a}{b}$$", "\\frac{a}{b}"),
        ("\\[ a+b \\]", "a+b"),
        ("```latex\n\\sqrt{x}\n```", "\\sqrt{x}"),
        ("LaTeX: \\alpha", "\\alpha"),
        ("Fixed transcribation: x squared\nLaTex: x^{2}", "x^{2}"),
        ("<think>hmm</think>y=mx+b", "y=mx+b"),
        ("x^{2}.", "x^{2}"),
        ("a\\,", "a\\,"),  # a trailing spacing command is not punctuation
        ("x\n+\ny", "x + y"),
    ],
)
def test_clean_equations(raw, expected):
    assert clean_output(raw, "equations") == expected


def test_clean_sentences_keeps_dollars():
    assert clean_output("Let $x=1$ hold.", "sentences") == "Let $x=1$ hold."
