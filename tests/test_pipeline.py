"""End-to-end harness test with stand-in backends (no MLX needed)."""

from pathlib import Path

import pytest

from ldbench import backends
from ldbench.config import load_config
from ldbench.data import fetch_parquet_sample
from ldbench.report import compute, write_report
from ldbench.runner import run_system

CALLS = {"asr": 0, "text": 0, "e2e": 0}


class FakeASR:
    def __init__(self, model, path):
        pass

    def transcribe(self, audio_path):
        CALLS["asr"] += 1
        return Path(audio_path).stem  # the item id stands in for a transcript


class FakeText:
    """Returns the right answer for 'human' items and a wrong one for 'tts' items."""

    def __init__(self, model, path):
        pass

    def generate(self, messages, max_tokens):
        CALLS["text"] += 1
        transcript = messages[-1]["content"].split(":", 1)[1].strip()
        return "```latex\n$x^{2}$\n```" if "human" in transcript else "y"


class FakeE2E:
    def __init__(self, model, path):
        pass

    def generate(self, audio_path, prompt, max_tokens):
        CALLS["e2e"] += 1
        return "LaTeX: x^2"


@pytest.fixture
def cfg(tmp_path, parquet_split, monkeypatch):
    monkeypatch.setitem(backends.ASR_KINDS, "fake-asr", FakeASR)
    monkeypatch.setitem(backends.TEXT_KINDS, "fake-text", FakeText)
    monkeypatch.setitem(backends.E2E_KINDS, "fake-e2e", FakeE2E)
    for k in CALLS:
        CALLS[k] = 0
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (tmp_path / "configs").mkdir()
    path = tmp_path / "configs" / "t.toml"
    path.write_text(f"""
run_name = "t"
[[splits]]
name = "equations"
source = "local"
path = "data/eq"
task = "equations"
[models.asr]
kind = "fake-asr"
repo = "{model_dir}"
[models.llm]
kind = "fake-text"
repo = "{model_dir}"
[models.e2e]
kind = "fake-e2e"
repo = "{model_dir}"
[[systems]]
name = "raw"
asr = "asr"
[[systems]]
name = "cascade"
asr = "asr"
text = "llm"
[[systems]]
name = "oracle"
asr = "column:pronunciation"
text = "llm"
[[systems]]
name = "missing-column"
asr = "column:no_such_column"
text = "llm"
[[systems]]
name = "audio-llm"
e2e = "e2e"
[gates]
max_peak_memory_gb = 12
max_p95_latency_s = 3.0
""")
    fetch_parquet_sample(parquet_split, lambda p: open(p, "rb"), tmp_path / "data" / "eq", "equations",
                         "equations", "eng", {"human": 4, "tts": 4}, seed=0, max_per_row_group=4)
    return load_config(path)


def test_pipeline_runs_caches_and_scores(cfg):
    for name in cfg.systems:
        run_system(cfg, name)
    # 8 clips: one warm-up + 8 timed ASR calls, shared by 'raw' and 'cascade'
    assert CALLS["asr"] == 9
    # text model: cascade and oracle, each warm-up + 8
    assert CALLS["text"] == 18
    assert CALLS["e2e"] == 9

    for name in cfg.systems:  # second run is fully cached
        run_system(cfg, name)
    assert CALLS == {"asr": 9, "text": 18, "e2e": 9}

    results = compute(cfg)
    eq = results["splits"]["equations"]["systems"]
    # cascade: human items exactly right (x^{2} vs reference x^{k}); not all exact because targets vary
    assert eq["cascade"]["n"] == 8 and eq["cascade"]["nonempty"] == 1.0
    assert set(eq["cascade"]["headline"]["cer_by_group"]) == {"human", "tts"}
    assert eq["audio-llm"]["status"] == "ok"
    assert eq["missing-column"]["status"].startswith("skipped")
    assert eq["oracle"]["latency_scope"].startswith("text step only")
    gate_systems = {g["system"] for g in results["gates"]}
    assert "raw" in gate_systems and "missing-column" in gate_systems

    report = write_report(cfg, results)
    text = report.read_text()
    assert "## equations" in text and "cascade" in text
    assert (cfg.run_dir / "examples.md").exists()


def test_resume_after_partial_run(cfg):
    run_system(cfg, "cascade", limit=3)
    assert CALLS["text"] == 4
    run_system(cfg, "cascade")
    assert CALLS["text"] == 4 + 1 + 5  # warm-up + the 5 remaining items
