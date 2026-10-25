import math

import pytest

from ldbench.metrics import (
    bootstrap_cer_ci,
    corpus_rates,
    latex_tokens,
    normalize_formula,
    normalize_sentence,
    percentile,
    score_item,
    sentence_formulas,
)


@pytest.mark.parametrize(
    "a,b",
    [
        ("x^2", "x^{2}"),
        ("\\left( a+b \\right)", "(a+b)"),
        ("\\dfrac{1}{2}", "\\frac12"),
        ("a \\, b", "ab"),
        ("$x \\le y$", "x\\leq y"),
        ("\\hat{\\mu}", "\\hat\\mu"),
        ("\\mathcal{X}", "\\mathcal X"),
        ("\\{x_1, x_2\\}", "{x_{1},x_{2}}"),  # the paper's references drop escaped set braces
        ("\\varepsilon", "\\epsilon"),
    ],
)
def test_equivalent_forms_normalize_equal(a, b):
    assert normalize_formula(a) == normalize_formula(b)


@pytest.mark.parametrize("a,b", [("x^{2y}", "x^2y"), ("\\frac{a}{b}+c", "\\frac{a+b}{c}"), ("\\alpha", "a")])
def test_different_formulas_stay_different(a, b):
    assert normalize_formula(a) != normalize_formula(b)


def test_tokens_keep_commands_whole():
    assert latex_tokens("\\alpha+\\beta") == ["\\alpha", "+", "\\beta"]


def test_equation_scores():
    s = score_item("x^2+1", "x^{2}+1", "equations")["latex"]
    assert s.exact and s.edits == 0 and s.ref_len == len("x^2+1")
    s = score_item("x^3+1", "x^{2}+1", "equations")["latex"]
    assert not s.exact and s.edits == 1 and s.tok_edits == 1


def test_corpus_cer_is_edit_weighted():
    a = score_item("ab", "ab", "equations")["latex"]  # 0 / 2
    b = score_item("x", "xyzw", "equations")["latex"]  # 3 / 4
    rates = corpus_rates([a, b])
    assert rates["cer"] == pytest.approx(3 / 6)
    assert rates["exact"] == 0.5


def test_sentence_views():
    ref = "Let $f(x)=x^{2}$ be a function."
    assert sentence_formulas(ref) == "f(x)=x^2"
    assert normalize_sentence("Let $f(x) = x^2$ be a function!") == normalize_sentence(ref)
    scores = score_item("Let $f(x)=x^3$ be a function.", ref, "sentences")
    assert scores["formulas"].edits == 1
    assert scores["full"].edits == 1


def test_sentence_without_math_in_prediction():
    scores = score_item("let f of x equal x squared", "Let $f(x)=x^{2}$.", "sentences")
    assert scores["formulas"].edits == len("f(x)=x^2")


def test_bootstrap_ci_contains_point_estimate():
    scores = [score_item(p, r, "equations")["latex"] for p, r in
              [("x", "x"), ("y", "x"), ("a+b", "a+b"), ("ab", "abc"), ("q", "q")] * 6]
    point = corpus_rates(scores)["cer"]
    lo, hi = bootstrap_cer_ci(scores, n_boot=500)
    assert lo <= point <= hi


def test_percentile():
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert math.isnan(percentile([], 0.5))


@pytest.mark.parametrize(
    "normalized,raw",
    [
        # forms seen in the dataset's sentence_normalized column vs ordinary LaTeX
        (r"\csc\\x=\frac{1}{\sin\\x}", r"\csc x = \frac{1}{\sin x}"),
        (r"{A_{2}f(x)}\leq\\M^{0}f(x)", r"A_2 f(x) \le M^0 f(x)"),
        (r"\lim_{{x\to\\4}}\sqrt{x}", r"\lim_{x \to 4} \sqrt{x}"),
        (r"\sigma^{\pm}=\frac{1}{2}(\sigma^{x}\pm\\i\sigma^{y})", r"\sigma^\pm = \frac12 (\sigma^x \pm i \sigma^y)"),
    ],
)
def test_dataset_normalized_form_matches_raw_latex(normalized, raw):
    assert normalize_formula(normalized) == normalize_formula(raw)


def test_argument_braces_are_kept():
    assert normalize_formula(r"\frac{a+b}{c}") != normalize_formula(r"\frac{a}{b}+c")
    assert normalize_formula(r"\sqrt[3]{x+1}") == r"\sqrt[3]{x+1}"
    assert normalize_formula(r"x^{2y}") != normalize_formula(r"x^2y")


def test_median_item_cer_ignores_one_runaway():
    from ldbench.metrics import median_item_cer

    good = [score_item("x+1", "x+1", "equations")["latex"]] * 4
    runaway = score_item("1,0,0,0,0,0,0,0,0,0,0,0", "R", "equations")["latex"]
    assert corpus_rates(good + [runaway])["cer"] > 1.0
    assert median_item_cer(good + [runaway]) == 0.0
