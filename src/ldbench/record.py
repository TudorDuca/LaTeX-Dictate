"""Record your own test formulas with the laptop microphone (16 kHz mono WAV)."""

from __future__ import annotations

import html
import wave
from pathlib import Path

from .data import build_local_manifest, read_formulas

SAMPLE_RATE = 16_000

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


def _save_wav(path: Path, chunks: list) -> float:
    import numpy as np

    audio = np.concatenate(chunks) if chunks else np.zeros((0, 1), dtype="int16")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(audio.tobytes())
    return len(audio) / SAMPLE_RATE


def record(own_dir: Path, only: list[str] | None = None, redo: bool = False) -> dict:
    import sounddevice as sd

    own_dir = Path(own_dir)
    formulas = read_formulas(own_dir)
    page = write_prompts_html(own_dir, formulas)
    print(INSTRUCTIONS.format(html=page))

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
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                            callback=lambda data, frames, t, status: chunks.append(data.copy())):
            input("  recording... Enter to stop > ")
        seconds = _save_wav(out, chunks)
        print(f"  saved {out.name} ({seconds:.1f} s)")
    return build_local_manifest(own_dir)
