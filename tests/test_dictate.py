"""Dictation daemon logic with stand-ins for keys, microphone, models and clipboard."""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from ldbench import backends
from ldbench.config import load_config
from ldbench.dictate import Dictation, HoldDetector, Pipeline, key_matches, max_tokens_for


# ---- pynput-like keys: KeyCode compares by (vk, char); Key members wrap a KeyCode in .value
@dataclass(frozen=True)
class KeyCode:
    vk: int | None = None
    char: str | None = None


@dataclass(frozen=True)
class Key:
    name: str
    value: KeyCode
    generic: str | None = None  # what canonical() maps a left/right modifier to


ALT_L = Key("alt_l", KeyCode(vk=0x3A), generic="alt")
ALT_R = Key("alt_r", KeyCode(vk=0x3D), generic="alt")
CTRL_L = Key("ctrl_l", KeyCode(vk=0x3B), generic="ctrl")
M = KeyCode(char="m")


def canonical(k):
    if isinstance(k, Key) and k.generic:
        return k.generic
    if isinstance(k, KeyCode) and k.char:
        return KeyCode(char=k.char.lower())
    return k


def test_right_option_hotkey_does_not_fire_on_left_option():
    combo = [KeyCode(vk=0x3D)]  # what HotKey.parse('<alt_r>') returns
    assert key_matches(ALT_R, combo[0], canonical)
    assert not key_matches(ALT_L, combo[0], canonical)


def test_generic_modifier_matches_either_side():
    assert key_matches(CTRL_L, "ctrl", canonical)
    assert key_matches(KeyCode(char="M"), M, canonical)


def test_letter_with_option_matches_by_physical_key():
    # macOS reports Option+M as "µ" but keeps the virtual key code of M
    assert key_matches(KeyCode(vk=0x2E, char="µ"), M, canonical)
    assert not key_matches(KeyCode(vk=0x2D, char="˜"), M, canonical)  # Option+N


def test_option_combo_held():
    events = []
    d = HoldDetector(["ctrl", "alt", M], canonical, events.append)
    d.press(CTRL_L)
    d.press(ALT_L)
    d.press(KeyCode(vk=0x2E, char="µ"))
    assert events == ["start"]
    d.release(ALT_L)
    d.release(KeyCode(vk=0x2E, char="m"))  # released after Option: reported as plain "m"
    assert events == ["start", "stop"] and d.pressed == {("vk", 0x3B): CTRL_L}


def test_hold_detector_start_stop():
    events = []
    d = HoldDetector(["ctrl", M], canonical, events.append)
    d.press(CTRL_L)
    assert events == []
    d.press(KeyCode(char="m"))
    d.press(KeyCode(char="m"))  # key repeat while held: no second start
    assert events == ["start"]
    d.release(KeyCode(char="m"))
    assert events == ["start", "stop"]
    d.release(CTRL_L)
    assert events == ["start", "stop"]


# ---- daemon flow
class FakeRecorder:
    rate = 16_000

    def __init__(self, seconds=1.0):
        self.seconds = seconds
        self.started = 0

    def start(self):
        self.started += 1

    def stop(self):
        return [np.full((int(self.seconds * self.rate), 1), 1000, dtype="int16")]


class FakePipeline:
    def __init__(self, latex="x^{2}", fail=False):
        self.latex, self.fail = latex, fail

    def __call__(self, wav):
        if self.fail:
            raise RuntimeError("boom")
        return {"transcript": "x squared", "raw": self.latex, "latex": self.latex, "asr_s": 0.3, "gen_s": 0.5}


def make(tmp_path, **kw):
    clip, pasted, lines = [], [], []
    options = {"wrap": "none", "do_paste": False, **{k: v for k, v in kw.items() if k in ("wrap", "do_paste")}}
    d = Dictation(kw.get("pipeline", FakePipeline()), kw.get("recorder", FakeRecorder()), sounds=False,
                  log_path=tmp_path / "log.jsonl", clipboard=clip.append, paster=lambda: pasted.append(1),
                  out=lines.append, **options)
    return d, clip, pasted, lines


def test_hold_flow_copies_and_logs(tmp_path):
    d, clip, pasted, lines = make(tmp_path, wrap="inline")
    d.handle("start")
    d.handle("start")  # ignored while recording
    d.handle("stop")
    assert clip == ["$x^{2}$"] and pasted == []
    rec = json.loads((tmp_path / "log.jsonl").read_text())
    assert rec["latex"] == "x^{2}" and rec["transcript"] == "x squared" and rec["audio"] is None


def test_toggle_and_paste(tmp_path):
    d, clip, pasted, _ = make(tmp_path, do_paste=True)
    d.handle("toggle")
    assert d.recording
    d.handle("toggle")
    assert not d.recording and clip == ["x^{2}"] and pasted == [1]


def test_short_take_is_ignored(tmp_path):
    d, clip, _, lines = make(tmp_path, recorder=FakeRecorder(seconds=0.1))
    d.handle("start")
    d.handle("stop")
    assert clip == [] and any("too short" in l for l in lines)


def test_pipeline_error_keeps_running(tmp_path):
    d, clip, _, lines = make(tmp_path, pipeline=FakePipeline(fail=True))
    d.handle("start")
    d.handle("stop")
    assert clip == [] and any("failed" in l for l in lines)
    assert d.handle("start") is True  # still alive


def test_quit_event(tmp_path):
    d, *_ = make(tmp_path)
    assert d.handle("quit") is False


def test_max_tokens_scales_with_speech():
    assert max_tokens_for("x squared", 256) == 44
    assert max_tokens_for("word " * 100, 256) == 256


# ---- pipeline wiring with stand-in models
class FakeASR:
    def __init__(self, model, path):
        pass

    def transcribe(self, audio_path):
        return "capital R C 1000,000"


class LoopingText:
    """Mimics the paper model's repetition loop; records the max_tokens it was given."""

    seen: list = []

    def __init__(self, model, path):
        pass

    def generate(self, messages, max_tokens):
        LoopingText.seen.append(max_tokens)
        return "R_{c}(" + "0," * max_tokens


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setitem(backends.ASR_KINDS, "fake-asr", FakeASR)
    monkeypatch.setitem(backends.TEXT_KINDS, "loop-text", LoopingText)
    (tmp_path / "m").mkdir()
    (tmp_path / "configs").mkdir()
    p = tmp_path / "configs" / "d.toml"
    p.write_text(f"""
run_name = "d"
[models.asr]
kind = "fake-asr"
repo = "{tmp_path / 'm'}"
[models.llm]
kind = "loop-text"
repo = "{tmp_path / 'm'}"
[[systems]]
name = "cascade"
asr = "asr"
text = "llm"
prompt = "paper"
[[systems]]
name = "oracle"
asr = "column:pronunciation"
text = "llm"
""")
    return load_config(p)


def test_pipeline_bounds_runaway_generation(cfg):
    LoopingText.seen.clear()
    out = Pipeline(cfg, "cascade", "equations")("clip.wav")
    assert LoopingText.seen == [32 + 6 * 4]
    assert out["transcript"] == "capital R C 1000,000" and out["latex"].startswith("R_{c}(")


def test_pipeline_rejects_dataset_transcript_systems(cfg):
    with pytest.raises(SystemExit, match="real ASR model"):
        Pipeline(cfg, "oracle", "equations")
