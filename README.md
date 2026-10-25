# LaTeX-Dictate

Speak mathematics and get correct LaTeX, using open models that run on a laptop.

This project benchmarks current open speech and language models on turning spoken maths into LaTeX,
using the open [Speech-to-LaTeX](https://github.com/dkorzh10/speech2latex) dataset (CC BY 4.0, ICLR 2026).
It then fine-tunes a small on-device model for Apple Silicon and turns it into a push-to-talk demo.

- **Plan:** [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md). It covers the research questions, scope, milestones, targets and the $0 resource plan.
- **Status:** M0 (feasibility) is done and the gate passed. See [docs/M0_RESULTS.md](docs/M0_RESULTS.md). The paper's fine-tuned 1.5B model is far ahead of open models without fine-tuning, everything runs within 8.4 GB at ≤2 s per formula, and fine-tuning becomes the core of the project. Next: M1, the full benchmark.

## Setup (macOS, Apple Silicon)

```bash
brew install ffmpeg uv node          # node is optional: it enables the KaTeX render-rate metric
git clone <this repo> && cd LaTeX-Dictate
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e '.[mac,record,dev]'
(cd tools/katex && npm install)      # optional
hf auth login                        # free Hugging Face account; needed if the dataset is gated
```

## M0 runbook

1. **Install check.** About 5 minutes, plus a ~4 GB model download. This uses 16 sample clips from the paper's repo, so it needs no dataset access.
   ```bash
   ldb all --config configs/smoke.toml
   open runs/smoke/report.md
   ```
2. **Pre-flight and model pinning.** This checks the machine, dataset access and every model repo, then writes `configs/m0.lock.json`. Commit that file.
   ```bash
   ldb doctor
   ```
3. **Record your 20 formulas.** About 10 minutes. Open `data/own/prompts.html` to see each formula rendered, and say it the way you would naturally dictate it.
   ```bash
   ldb record                       # uses the default input at its native rate
   ldb record --list-devices        # if the mic won't open: pick one with --device <index>
   ldb record --only f07 --redo     # re-record one formula later
   ```
   After each take you can keep it, redo it, or play it back. Keep "um"s, pauses and your own
   phrasing, because that is natural dictation. Redo only if you said a different formula, left part out, or got cut off.
   If the mic still won't open, check System Settings > Privacy & Security > Microphone for your terminal app.
   Or record with Voice Memos or QuickTime and save each take as `data/own/audio/<id>.m4a`.
   `ldb fetch` converts those files.
4. **Run M0.** Expect about 15–20 GB of model downloads the first time. After that the run takes well under an hour.
   ```bash
   ldb all            # fetch the sample, run every system (one process each), score
   open runs/m0/report.md runs/m0/examples.md
   ```
   Runs can be resumed: finished items are cached, so rerunning only does what's missing.
   If something fails, rerun the same command, or run one system with `ldb run --system <name>`, then `ldb score`.
   To recompute from scratch, add `--fresh`, which deletes that system's cached results first.

### What M0 runs

| System | What it is |
|---|---|
| `whisper-raw` | Whisper-large-v3-turbo only. Shows how plain dictation does |
| `paper@dataset-asr` | Reproduces the paper's setup: their fine-tuned Qwen2.5-math-1.5B, run on the dataset's own Whisper transcripts |
| `paper@whisper-turbo` | The paper's model, run on our Whisper transcripts |
| `qwen3-4b@whisper-turbo` | Open pipeline, no fine-tuning: Whisper → Qwen3-4B-Instruct (4-bit) |
| `qwen3-4b@oracle` | The same LLM given the dataset's ground-truth pronunciation, a ceiling for the text step |
| `qwen2-audio@e2e` | Open audio LLM, no fine-tuning: audio goes straight to LaTeX |

**Data:**
- 40 human-recorded and 10 TTS English equations, plus 10 human-recorded English sentences. These are a seeded random sample of the S2L test splits, read directly from the parquet files, so the full 320 GB dataset is never downloaded.
- Your own recordings.

**The report shows:**
- CER with bootstrap 95% confidence intervals, token error rate and exact match.
- KaTeX render rate.
- p50/p95 latency and peak memory per model.
- The M0 gate checks: ≤12 GB peak memory and ≤3 s p95 latency.

## Try it: push-to-talk maths dictation

Hold a key, say a formula, let go, and the LaTeX is pasted where your cursor is, in any app. It also stays on the clipboard.
The default is Whisper-turbo plus the paper's fine-tuned model, the best system in M0, running fully on-device.

```bash
uv pip install -e '.[mac,dictate]'
ldb dictate                         # hold right Option (⌥), speak, release
```

- **First run:** macOS asks for **Microphone** access. Allow it.
- **Hotkeys and pasting** need your terminal app enabled under System Settings > Privacy & Security, in two places:
  - **Input Monitoring**, to hear the hotkey;
  - **Accessibility**, to paste. Without it the paste is dropped silently, and `ldb dictate` warns at startup.

  Restart the terminal after enabling them.
- **Options:**
  - `--wrap inline` gives `$...$`; `--wrap display` gives `\[...\]`.
  - `--type` types the text key by key, for apps that ignore a pasted ⌘V. `--copy-only` leaves it on the clipboard without pasting.
  - `--mode toggle` uses press-to-start, press-to-stop (default hotkey `<ctrl>+<alt>+m`). `--hotkey` sets any combination.
  - `--mode terminal` uses Enter in the terminal window and needs no Accessibility permission.
  - `--task sentences` handles prose with inline maths.
- **Talking normally, with maths inline:** `ldb dictate --task mixed`. This is for explaining your reasoning to an AI tutor, writing notes, and similar. Whisper transcribes everything, and Qwen3-4B marks which words are maths. Only those spans go to the equation model, so your own words come through exactly as heard: "so if f of x equals x squared then the derivative is two x" becomes "so if $f(x)=x^{2}$ then the derivative is $2x$". It keeps about 11 GB of models loaded.
- **Other models:** any system from `configs/m0.toml`, for example `ldb dictate --system qwen3-4b@whisper-turbo`.
- **What it costs to run:** it keeps about 8.4 GB of models in memory while running, so quit with Ctrl+C when you're done. Each dictation takes about 1 s.
- **Logging:** each dictation is logged locally to `runs/dictate/log.jsonl`. `--save-audio` also keeps the recordings under `data/dictations/audio/`. Neither is committed to git. Your own takes are useful test data later.

## Layout

```
configs/         benchmark configs (+ .lock.json model pins)
src/ldbench/     harness: data sampling, backends (MLX), runner, metrics, report
tools/katex/     Node-based KaTeX render check
data/own/        your formulas (formulas.csv); recordings stay local
tests/           pytest suite (runs anywhere, no MLX needed)
```
