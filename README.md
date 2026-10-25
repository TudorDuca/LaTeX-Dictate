# LaTeX-Dictate

Speak mathematics and get correct LaTeX, using open models that run on a laptop.

This project benchmarks current open speech and language models on turning spoken maths into LaTeX,
using the open [Speech-to-LaTeX](https://github.com/dkorzh10/speech2latex) dataset (CC BY 4.0, ICLR 2026).
It then fine-tunes a small on-device model for Apple Silicon and turns it into a push-to-talk demo.

- **Plan:** [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md). It covers the research questions, scope, milestones, targets and the $0 resource plan.
- **Status:** M0 (feasibility). The harness is ready and waiting for its first run on an M5 MacBook.

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
   ldb record
   ```
4. **Run M0.** Expect about 15–20 GB of model downloads the first time. After that the run takes well under an hour.
   ```bash
   ldb all            # fetch the sample, run every system (one process each), score
   open runs/m0/report.md runs/m0/examples.md
   ```
   Runs can be resumed. If something fails, rerun the same command, or run one system with
   `ldb run --system <name>`, then `ldb score`.

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

## Layout

```
configs/         benchmark configs (+ .lock.json model pins)
src/ldbench/     harness: data sampling, backends (MLX), runner, metrics, report
tools/katex/     Node-based KaTeX render check
data/own/        your formulas (formulas.csv); recordings stay local
tests/           pytest suite (runs anywhere, no MLX needed)
```
