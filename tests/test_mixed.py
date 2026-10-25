"""Split-then-convert: prose comes from the transcript, only maths spans are converted."""

import pytest

from ldbench.metrics import score_item
from ldbench.mixed import align_labels, convert_mixed, parse_tagged, spans

SPOKEN = {"f of x equals x squared": "f(x)=x^{2}", "two x": "2x", "p": "p", "q": "q",
          "the integral from zero to one of x dx": "\\int_0^1 x\\,dx"}


def fake_converter(spoken):
    return SPOKEN.get(spoken, "")


def segmenter_returning(tagged):
    calls = []

    def segment(messages, max_tokens):
        calls.append(messages[-1]["content"])
        return tagged

    segment.calls = calls
    return segment


def test_basic_mixed_output():
    t = "so if f of x equals x squared, then the derivative is two x."
    seg = segmenter_returning("so if <m>f of x equals x squared</m>, then the derivative is <m>two x</m>.")
    out = convert_mixed(t, seg, fake_converter)
    assert out["text"] == "so if $f(x)=x^{2}$, then the derivative is $2x$."
    assert seg.calls == [t]
    assert [s["spoken"] for s in out["spans"]] == ["f of x equals x squared", "two x"]


def test_prose_is_kept_even_if_segmenter_rewrites_it():
    t = "um so I think that p and q are coprime"
    # the segmenter dropped "um" and changed "I think that" -> "we know"
    seg = segmenter_returning("so we know <m>p</m> and <m>q</m> are coprime")
    out = convert_mixed(t, seg, fake_converter)
    assert out["text"] == "um so I think that $p$ and $q$ are coprime"


def test_failed_conversion_keeps_the_words():
    t = "and then zeta of s converges"
    out = convert_mixed(t, segmenter_returning("and then <m>zeta of s</m> converges"), fake_converter)
    assert out["text"] == "and then zeta of s converges"


def test_no_maths_passes_through():
    t = "can you explain the chain rule again?"
    assert convert_mixed(t, segmenter_returning(t), fake_converter)["text"] == t


def test_rewritten_word_inside_a_formula_stays_maths():
    words = "f of x equals x squared".split()
    tagged = parse_tagged("<m>f of x equal x squared</m>")  # "equals" -> "equal"
    assert all(align_labels(words, tagged))


def test_spans_split_edge_punctuation():
    words = ["is", "(x+1),", "right"]
    out = spans(words, [False, True, False])
    assert out[1] == (True, "(", "x+1", "),")


def test_prose_metric_rewards_verbatim_prose():
    ref = "so if $f(x)=x^{2}$ then the derivative is $2x$"
    kept = score_item("so if $f(x)=x^2$ then the derivative is $2x$", ref, "sentences")
    rewritten = score_item("thus if $f(x)=x^2$ its derivative equals $2x$", ref, "sentences")
    assert kept["prose"].tok_edits == 0 and kept["formulas"].edits == 0
    assert rewritten["prose"].tok_edits > 0 and rewritten["formulas"].edits == 0


def test_runner_and_report_with_split_system(tmp_path, monkeypatch):
    import json

    from ldbench import backends
    from ldbench.config import load_config
    from ldbench.report import compute
    from ldbench.runner import run_system

    class Seg:
        def __init__(self, model, path):
            pass

        def generate(self, messages, max_tokens):
            return messages[-1]["content"].replace("x squared", "<m>x squared</m>")

    class Conv:
        def __init__(self, model, path):
            pass

        def generate(self, messages, max_tokens):
            return "x^{2}" if "x squared" in messages[-1]["content"] else ""

    monkeypatch.setitem(backends.TEXT_KINDS, "seg", Seg)
    monkeypatch.setitem(backends.TEXT_KINDS, "conv", Conv)
    split_dir = tmp_path / "data" / "sent"
    split_dir.mkdir(parents=True)
    rows = [{"id": "a", "group": "human", "target": "so $x^{2}$ is positive", "audio": "a.wav",
             "whisper_text": "so x squared is positive"},
            {"id": "b", "group": "human", "target": "hence $x^{2}\\geq 0$", "audio": "b.wav",
             "whisper_text": "hence x squared is at least zero"}]
    (split_dir / "manifest.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (tmp_path / "m").mkdir()
    (tmp_path / "configs").mkdir()
    cfg_path = tmp_path / "configs" / "s.toml"
    cfg_path.write_text(f"""
run_name = "s"
[[splits]]
name = "sentences"
source = "local"
path = "data/sent"
task = "sentences"
[models.seg]
kind = "seg"
repo = "{tmp_path / 'm'}"
[models.conv]
kind = "conv"
repo = "{tmp_path / 'm'}"
[[systems]]
name = "split"
asr = "column:whisper_text"
segmenter = "seg"
text = {{ sentences = "conv" }}
prompt = "paper"
""")
    cfg = load_config(cfg_path)
    run_system(cfg, "split")
    preds = [json.loads(l) for l in (cfg.run_dir / "sentences" / "pred" / "split.jsonl").read_text().splitlines()]
    assert preds[0]["pred"] == "so $x^{2}$ is positive"
    assert preds[1]["pred"] == "hence $x^{2}$ is at least zero"
    res = compute(cfg)["splits"]["sentences"]["systems"]["split"]
    assert res["views"]["formulas"]["cer"] < 1 and "prose" in res["views"]
