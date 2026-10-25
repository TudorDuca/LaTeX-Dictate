"""Record your own test formulas with the laptop microphone (mono WAV at the device's native rate)."""

from __future__ import annotations

import html
import wave
from pathlib import Path

from .data import build_local_manifest, read_formulas

# Below this peak level (int16 full scale = 32767) a take is treated as silent.
SILENCE_PEAK = 300

OPEN_FAILED = """\
Could not open the microphone ({error}).

Things to check:
  1. System Settings > Privacy & Security > Microphone: allow your terminal app
     (Terminal, iTerm, VS Code...), then restart it.
  2. Pick an input explicitly:  ldb record --list-devices   then   ldb record --device <index or name>
  3. Or record elsewhere (Voice Memos, QuickTime) and save each take as
     {audio_dir}/<id>.m4a (or .wav/.mp3); `ldb fetch` converts them.
"""

INSTRUCTIONS = """\
Recording your own formulas
---------------------------
Open {html} in a browser to see each formula rendered.
For each one: look at the rendered formula and say it the way you would naturally dictate it
to a colleague. Don't read LaTeX command names, and don't rehearse; hesitations are fine.
Controls: Enter = start, Enter = stop. Type 's' + Enter to skip, 'q' + Enter to quit.
"""


def write_prompts_html(own_dir: Path, formulas: list[dict]) -> Path:
    rows = "\n".join(
        f"<tr><td>{html.escape(f['id'])}</td><td>{html.escape(f.get('difficulty', ''))}</td>"
        f"<td class='m'>\\[{html.escape(f['latex'])}\\]</td></tr>"
        for f in formulas
    )
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Formulas to record</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body)"></script>
<style>body{{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}}
td{{padding:.6rem 1rem;border-bottom:1px solid #ddd}} td.m{{font-size:1.3rem}}</style></head>
<body><h1>Formulas to record</h1>
<p>Say each formula the way you would naturally dictate it. Don't read LaTeX command names.</p>
<table>{rows}</table></body></html>"""
    out = Path(own_dir) / "prompts.html"
    out.write_text(page)
    return out


def save_wav(path: Path, chunks: list, rate: int) -> tuple[float, int]:
    """Write int16 mono chunks; returns (seconds, peak level)."""
    import numpy as np

    audio = np.concatenate(chunks) if chunks else np.zeros((0, 1), dtype="int16")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(audio.tobytes())
    peak = int(np.abs(audio.astype("int32")).max()) if len(audio) else 0
    return len(audio) / rate, peak


def _device_arg(device: str | None):
    if device is None:
        return None
    return int(device) if device.isdigit() else device


def list_devices() -> str:
    import sounddevice as sd

    return str(sd.query_devices())


def record(own_dir: Path, only: list[str] | None = None, redo: bool = False,
           device: str | None = None) -> dict:
    import sounddevice as sd

    own_dir = Path(own_dir)
    formulas = read_formulas(own_dir)
    page = write_prompts_html(own_dir, formulas)

    dev = _device_arg(device)
    try:
        info = sd.query_devices(dev, kind="input")
    except (sd.PortAudioError, ValueError) as e:
        raise SystemExit(OPEN_FAILED.format(error=e, audio_dir=own_dir / "audio")) from e
    # Mac input devices generally open only at their native rate (44.1/48 kHz); asking for 16 kHz
    # fails with "Invalid Property Value". Record natively; every backend resamples on load.
    rate = int(info["default_samplerate"])
    print(INSTRUCTIONS.format(html=page))
    print(f"Input device: {info['name']} ({rate} Hz)")

    todo = [f for f in formulas if (not only or f["id"] in only)]
    for k, f in enumerate(todo, 1):
        out = own_dir / "audio" / f"{f['id']}.wav"
        if out.exists() and not redo:
            continue
        print(f"\n[{k}/{len(todo)}] {f['id']}  ({f.get('difficulty', '')})\n    {f['latex']}")
        cmd = input("  Enter to start > ").strip().lower()
        if cmd == "q":
            break
        if cmd == "s":
            continue
        chunks: list = []
        try:
            stream = sd.InputStream(samplerate=rate, channels=1, dtype="int16", device=dev,
                                    callback=lambda data, frames, t, status: chunks.append(data.copy()))
        except sd.PortAudioError as e:
            raise SystemExit(OPEN_FAILED.format(error=e, audio_dir=own_dir / "audio")) from e
        with stream:
            input("  recording... Enter to stop > ")
        seconds, peak = save_wav(out, chunks, rate)
        print(f"  saved {out.name} ({seconds:.1f} s)")
        if peak < SILENCE_PEAK:
            print("  ! this take is (almost) silent: check the microphone permission for your terminal\n"
                  f"    app, then re-record with: ldb record --only {f['id']} --redo")
    return build_local_manifest(own_dir)
