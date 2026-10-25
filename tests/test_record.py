"""Recorder flow with a stand-in `sounddevice` module (no audio hardware needed)."""

import shutil
import subprocess
import sys
import types
import wave

import numpy as np
import pytest

from ldbench.data import build_local_manifest, read_manifest
from ldbench.record import record

from .conftest import make_wav


class FakePortAudioError(Exception):
    pass


def fake_sounddevice(rate=48_000, level=5000, fail_open=False):
    sd = types.ModuleType("sounddevice")
    sd.PortAudioError = FakePortAudioError
    opened = {}

    def query_devices(device=None, kind=None):
        return {"name": "MacBook Pro Microphone", "default_samplerate": float(rate)}

    class InputStream:
        def __init__(self, samplerate, channels, dtype, device, callback):
            if fail_open:
                raise FakePortAudioError("Internal PortAudio error [PaErrorCode -9986]")
            opened["samplerate"] = samplerate
            opened["streams"] = opened.get("streams", 0) + 1
            self.callback = callback

        def __enter__(self):
            # half a second of a tone at the requested rate
            n = int(0.5 * opened["samplerate"])
            data = (level * np.sin(np.arange(n) / 10)).astype("int16").reshape(-1, 1)
            self.callback(data, n, None, None)
            return self

        def __exit__(self, *exc):
            return False

    def play(audio, samplerate):
        opened["played"] = opened.get("played", 0) + 1

    sd.query_devices = query_devices
    sd.InputStream = InputStream
    sd.play = play
    sd.wait = lambda: None
    return sd, opened


@pytest.fixture
def own_dir(tmp_path):
    (tmp_path / "formulas.csv").write_text("id,difficulty,latex\nf01,easy,x^{2}\nf02,easy,y\n")
    return tmp_path


def test_records_at_device_native_rate(own_dir, monkeypatch, capsys):
    sd, opened = fake_sounddevice(rate=48_000)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)
    answers = iter(["", "", "", "s"])  # f01: start, stop, keep; f02: skip
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    stats = record(own_dir)
    assert opened["samplerate"] == 48_000
    with wave.open(str(own_dir / "audio" / "f01.wav")) as w:
        assert w.getframerate() == 48_000 and w.getnchannels() == 1
    assert stats["sampled"]["own"] == 1 and stats["missing_recordings"] == ["f02"]
    assert "silent" not in capsys.readouterr().out


def test_warns_on_silent_take(own_dir, monkeypatch, capsys):
    sd, _ = fake_sounddevice(level=0)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)
    answers = iter(["", "", "", "q"])  # f01: start, stop, keep; then quit
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    record(own_dir)
    assert "silent" in capsys.readouterr().out


def test_play_back_and_redo_a_take(own_dir, monkeypatch):
    sd, opened = fake_sounddevice()
    monkeypatch.setitem(sys.modules, "sounddevice", sd)
    # f01: start, stop, play back, redo, start redo, stop, keep; f02: quit
    answers = iter(["", "", "p", "r", "", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    stats = record(own_dir)
    assert opened["played"] == 1 and opened["streams"] == 2
    assert stats["sampled"]["own"] == 1


def test_open_failure_explains_fixes(own_dir, monkeypatch):
    sd, _ = fake_sounddevice(fail_open=True)
    monkeypatch.setitem(sys.modules, "sounddevice", sd)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    with pytest.raises(SystemExit) as e:
        record(own_dir)
    assert "Privacy & Security" in str(e.value) and "--device" in str(e.value)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_dropped_in_m4a_is_converted(own_dir):
    audio = own_dir / "audio"
    audio.mkdir()
    (audio / "src.wav").write_bytes(make_wav())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(audio / "src.wav"), str(audio / "f02.m4a")],
                   check=True)
    (audio / "src.wav").unlink()
    stats = build_local_manifest(own_dir)
    items = read_manifest(own_dir)
    assert [i["id"] for i in items] == ["f02"]
    assert items[0]["format"] == "wav" and items[0]["sample_rate"] == 16_000
    assert stats["missing_recordings"] == ["f01"]
