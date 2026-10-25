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


def test_paper_space_markers_become_spaces():
    raw = r"Integrating by parts $\int\\xe^{x}dx=x\\e^{x}-\int\\e^{x}dx=x\\e^{x}-e^{x}+C$."
    assert clean_output(raw, "sentences") == r"Integrating by parts $\int xe^{x}dx=x e^{x}-\int e^{x}dx=x e^{x}-e^{x}+C$."
    assert clean_output(r"\csc\\x=\frac{1}{\sin\\x}", "equations") == r"\csc x=\frac{1}{\sin x}"


def test_matrix_row_breaks_are_kept():
    raw = r"\begin{pmatrix}a&b\\c&d\end{pmatrix}\\x"
    assert clean_output(raw, "equations") == r"\begin{pmatrix}a&b\\c&d\end{pmatrix} x"


def test_language_note_only_for_non_english():
    from ldbench.prompts import text_messages

    es = text_messages("zero-shot", "sentences", "si f de x", "Spanish")[0]["content"]
    en = text_messages("zero-shot", "sentences", "if f of x", "English")[0]["content"]
    bench = text_messages("zero-shot", "sentences", "if f of x")[0]["content"]
    assert "in Spanish" in es and "never translate" in es
    assert en == bench and "never translate" not in bench
