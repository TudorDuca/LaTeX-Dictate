# LaTeX-Dictate — Project Plan

**Status:** draft for review. No code yet; this document decides what gets built.

**One line:** speak mathematics and get correct LaTeX: fast, private by default, and fixable by voice.

---

## 1. Problem

General-purpose dictation is now very good for prose and very bad for maths. When you say
"the integral from zero to infinity of e to the minus x squared dx", ASR either gives you the
words or a garbled mix of symbols. Writing LaTeX by hand is slow, and for some people it isn't possible at all.

**Who has this problem, most acute first:**

1. People who can't type much or at all: RSI, motor impairments, temporary injuries.
2. Blind and low-vision STEM students and researchers.
3. Heavy maths writers: lecture notes, papers, problem sheets, teaching material.

**Why now:**

- **A dataset now exists.** Speech-to-LaTeX (ICLR 2026) released the first large open dataset for this task, licensed **CC BY 4.0**. It has 66k human recordings and 571k synthetic ones, in English and Russian.
- **The best models haven't been tested.** The published state of the art comes from small, older open models: about 27% character error rate (CER) on equations and about 40% on sentences with maths in them. Nobody has published how current frontier audio and text models do on this benchmark.
- **Laptops can run this now.** Small models run locally on Apple Silicon through MLX, so offline, private, low-latency maths dictation is realistic.

## 2. Goal and guiding principles

**Goal:** find out how far current technology is from "dictating maths just works," close as much of the gap as
possible with a model that runs on a laptop, and show it in a usable prototype.

**Principles:**

- **Measure before building.** Every engineering choice comes from a benchmark number, not a guess.
- **Local first.** The default runs on-device, because voice is personal data. Cloud is an optional "max accuracy" mode.
- **Corrections matter as much as first-try accuracy.** Spoken maths is ambiguous: "x plus y over z" can mean two different things. A good system makes fixing errors cheap.
- **Reproducible.** Pinned model versions, scripts that recreate every number, open code and open results.

## 3. Research questions and hypotheses

Each question has a hypothesis and a decision attached, so whichever way the result goes, it tells us what to do next.

| # | Question | Hypothesis | If true, we… | If false, we… |
|---|---|---|---|---|
| RQ1 | How do today's frontier systems (no training) compare with the published state of the art on S2L? | They are clearly better: ≥10 CER points below the paper's best. | Treat the model as "mostly solved." Focus shifts to on-device performance, correction and UX. | Model work becomes the core of the project (Phase 3 grows). |
| RQ2 | What kinds of errors remain? | Most of them are about structure or scope (fractions, exponents, brackets), not misheard symbols. | Invest in voice correction and disambiguation UX. | Invest in acoustics (ASR fine-tuning, custom vocabulary). |
| RQ3 | Can a small model running on a 16 GB Mac match the best cloud system? | Yes: a LoRA-tuned model of 1.5–4B parameters gets within 5 CER points, at under 1.5 s latency. | Ship local-first as the default. | Cloud becomes the default and local is the private fallback. |
| RQ4 | Do benchmark results hold up for real, unscripted dictation? | No: real dictation is noticeably worse, because the benchmark is people reading scripts. | Our own real-dictation test set becomes a key contribution. | The S2L benchmark is enough on its own. |
| RQ5 | Is voice plus correction actually faster than typing LaTeX for our target users? | Yes, for medium and complex formulas. | There is evidence for a product or venture. | It stays a research and portfolio project. |

## 4. Scope

**In scope (v1)**

- English.
- Two tasks:
  - **Equations:** a single spoken formula becomes LaTeX.
  - **Sentences:** prose with maths in it becomes text with inline `$…$`.
- macOS on Apple Silicon (M5, 16 GB) for local models, plus cloud APIs for comparison.
- A benchmark harness, error analysis, a small fine-tuned model and a push-to-talk prototype.

**Out of scope (v1)**, possible later:

- Other languages. The dataset also has Russian; German or others would need new data.
- Moving around and editing a whole document by voice. v1 does single insertions plus corrections.
- Mobile, handwriting or OCR input, and braille/Nemeth output.
- Training a speech recognizer from scratch, or downloading the full 320 GB dataset.
- Streaming partial results while you're still speaking (a stretch goal for Phase 4).

## 5. Approach

### 5.1 The systems we compare

The test data is a sample of the S2L **test** splits, English only. Human and TTS recordings are reported separately.
We stream it rather than download it.

| Family | Pipeline | Why it's in the comparison |
|---|---|---|
| Floor | Whisper only, no conversion step | Shows how badly plain dictation does today |
| Paper reproduction | Whisper → the authors' released fine-tuned Qwen2.5 (0.5B–1.5B) | Validates our harness against published numbers |
| Cascade, local | Whisper-large-v3-turbo (MLX) → open 7–8B instruct model, 4-bit (MLX) | What runs offline today with no training |
| Cascade, cloud | Speech-to-text (Whisper / commercial) → frontier text LLM (Claude, GPT, Gemini) | The best text-conversion step available |
| End-to-end audio | Audio goes straight into an LLM that accepts audio (Gemini, OpenAI audio models, an open omni-model if one runs on MLX) | Tests whether skipping the transcript helps |
| **Oracle** | The dataset's correct pronunciation text → LLM | Puts a ceiling on the conversion step, which separates ASR errors from LaTeX errors |
| Ours (Phase 3) | Whisper → small LoRA-tuned model (MLX) | Answers RQ3 |

Exact model versions are pinned in the benchmark config and listed in every results table, because API models change.

### 5.2 Metrics

- **CER on normalized LaTeX.** This is the headline number. It uses the paper's own normalizer and evaluation code (MIT-licensed), so our numbers are directly comparable to theirs.
- **Token error rate** and **exact match** after normalization.
- **Render rate:** the share of outputs that compile in KaTeX.
- **Render-equivalent match (stretch):** both outputs render to the same normalized MathML. This catches cases CER treats unfairly, such as `\frac{a}{b}` vs `{a \over b}`.
- **Latency:** p50 and p95, measured from the end of speech.
- **Cost** per 1,000 formulas, and whether the system works offline.
- **Statistics:** bootstrap 95% confidence intervals, and paired comparisons between systems on the same clips.

### 5.3 Key feasibility insight: train the text step, not the audio step

The S2L training split already includes a Whisper transcript for every clip, paired with its LaTeX. That means we
can fine-tune the **transcript → LaTeX** model on text alone. That's small, fast and fits on the M5. We never need the
320 GB of audio for training. Fine-tuning the speech model itself is optional and would run on a rented GPU.

## 6. Phases, deliverables and go/no-go gates

Effort estimates assume about 8–10 hours a week. Total: about 14 weeks, roughly one semester.

### Phase 0 — Feasibility check (week 1). Budget: about $5

- Stream a small slice of the test splits and confirm access, columns, real split sizes and audio format.
- Run 50 clips through three systems: local cascade, cloud cascade and one end-to-end audio model.
- Measure peak RAM and latency on the M5.
- Record 20 formulas yourself.
- **Gate:** the pipeline works end to end. Local inference uses ≤12 GB RAM and takes ≤3 s per formula. We have first numbers for RQ1. Then **decide the emphasis:** model work (Phase 3) vs. product work (Phases 4–5).

### Phase 1 — Benchmark (weeks 2–4). Budget: about $30–80 in API costs

- Build the harness: per-stage caching, resumable runs, and one command per system.
- Sample: about 500 human-recorded English equations, 250 TTS English equations and 300 human-recorded English sentences. Expand if confidence intervals are too wide.
- Reproduce the paper's baseline using their evaluation script.
- **Deliverable:** results table, plots and a short technical report answering RQ1.
- **Gate:** our reproduction is within about 3 CER points of the paper's reported number. Otherwise the harness is wrong, and we fix it before going further.

### Phase 2 — Error analysis and real-dictation set (weeks 5–6)

- Hand-label about 200 errors from the best 2–3 systems into a taxonomy: misheard symbol, structure or scope, notation convention, formatting, hallucination.
- **RealDictation-100:** 100–200 formulas spoken naturally, not read from a script, by 5–10 people on ordinary laptop mics with different accents.
  - Voice recordings are personal data under the GDPR, so this needs a written consent form.
  - Publish it under CC BY only if the consent covers that.
- **Deliverable:** the taxonomy, plus the gap between scripted and natural speech. This answers RQ2 and RQ4.

### Phase 3 — On-device model (weeks 7–10). Budget: $0 local, plus an optional $10–50 for GPU rental

Each step is kept only if it beats the previous one:

1. Prompt engineering.
2. Retrieval-based few-shot examples.
3. LoRA fine-tune of a 1.5–4B model with MLX on S2L transcript → LaTeX pairs.
4. Optional: synthetic data, generated by reading arXiv LaTeX aloud with TTS.

Also fine-tune Whisper on maths audio, on a GPU paid for by the Google Cloud credit (§8.1) or a university cluster.

Check the license terms before training on any API model's outputs. Some providers restrict using outputs to train other models.

- **Deliverable:** an open model with a model card. Answers RQ3.

### Phase 4 — Prototype (weeks 9–12, overlapping Phase 3)

- Push-to-talk hotkey → record → LaTeX → live KaTeX preview → insert at the cursor. Insertion works in any editor (Overleaf, VS Code, Obsidian, Word) via the clipboard.
- **Voice corrections,** for example: "undo", "make that a fraction", "square the whole thing", "subscript i". Each one is implemented as an edit to the current LaTeX.
- Two modes: Local (default, private) and Cloud (best accuracy).
- **Stack:** a Python backend with a small web UI first, because it's fastest to build. Package it as a native app only if Phase 5 justifies it.
- **Deliverable:** a working demo and a 2-minute video.

### Phase 5 — User validation (weeks 12–14)

- 5–10 participants, including at least 2–3 from the accessibility target group. Your university's disability services office may help recruit.
- **Task:** enter 10 formulas of increasing difficulty by typing LaTeX vs. by dictating.
- **Measure:** time per formula, number of corrections, final correctness and a System Usability Scale (SUS) questionnaire.
- Check whether your university requires ethics approval for a study with human participants.
- **Deliverable:** evidence for RQ5 and a final report.

## 7. Targets

These are provisional. We revise them after Phase 0, once real numbers exist.

| Area | Minimum | Target | Stretch |
|---|---|---|---|
| Harness validity | Paper baseline reproduced within ±3 CER pts | — | — |
| Best system, human English equations (CER) | Report it | ≤15% (about half the published state of the art) | ≤10% |
| Best system, English sentences (equation CER) | Report it | ≤25% | ≤15% |
| Render rate | ≥95% | ≥98% | ≥99.5% |
| Local model vs. best cloud system | Within 10 pts | Within 5 pts | Matches it |
| Local latency (p95, M5) | ≤3 s | ≤1.5 s | ≤0.8 s |
| Local peak RAM | ≤12 GB | ≤8 GB | ≤5 GB |
| User study | Done with n ≥ 5 | Dictation faster than typing on medium/complex formulas; SUS ≥ 70 | SUS ≥ 80 |

## 8. Resources and feasibility

| Work | Where it runs | Fits on M5 / 16 GB? | Notes |
|---|---|---|---|
| Benchmark audio sample (~1–2k clips) | Local disk | Yes, under 1 GB | Streamed. We never download the 320 GB dataset |
| Whisper-large-v3-turbo inference (MLX) | Local | Yes, about 2 GB | |
| 7–8B LLM inference, 4-bit (MLX) | Local | Yes, about 5 GB | |
| Both running at once | Local | Yes, about 7–8 GB | Stages can also run one after the other |
| LoRA training of a 1.5–4B text model | Local | Yes | Roughly hours. Text-only data |
| QLoRA training of a 7–8B model | Local | Tight | Batch size 1 and short sequences. Optional |
| Whisper or audio-LLM fine-tuning | Rented GPU or university cluster | No | Optional. Estimated $10–50 |
| Cloud API benchmarking | API | n/a | Estimated $30–80 total. See below |

**On using the SSD ("permanent memory") as extra RAM:** macOS already does this automatically through swap. That's fine for an occasional spike during
inference. Training while swapping is 10–100× slower and wears the SSD, so the plan is designed to fit in RAM instead.
Keep about 25 GB of free disk for model weights, caches and data.

**Cost sketch.** These are estimates, so check current price pages:

- A frontier-tier text LLM at about $4 per million input tokens and $20 per million output tokens costs roughly **$10–15 per 1,000 formulas**, including some reasoning tokens.
- Small-tier models cost cents per 1,000.
- Audio-input models and commercial speech-to-text are a similar order of magnitude or cheaper. Check before running.
- Whole project: about **$50–150**, including optional GPU rental.
- Student and research credit programs, or a university GPU cluster, could bring this to roughly zero.

**Time:** about 14 weeks at 8–10 h/week. The benchmark (Phases 0–2) is valuable even if the project stops there.

### 8.1 Google Cloud free trial ($300 for 90 days)

These terms are from community guides. Check them on Google's free-trial page before signing up.

- **What the credit covers:**
  - Gemini models called **through Vertex AI** (the audio-input systems in the benchmark).
  - Google Speech-to-Text, which can serve as an extra commercial speech-to-text step in the cascades.
  - Storage, and GPU VMs, but GPUs only after upgrading (next point).
- **GPUs are blocked during the trial.** You must upgrade to a paid account. Upgrading keeps the unused credit until day 90, but from then on any spend beyond the credit is charged to your card. New accounts may also have to request GPU quota, and a request can be denied or take a few days.
- **What it reportedly doesn't cover:** Gemini through an AI Studio API key (use Vertex instead), and partner models on Vertex, Claude included. Anthropic and OpenAI usage stays a separate budget, estimated at $20–50.
- **When to start it:** at the start of Phase 1, not before. Cloud use spans Phase 1 (weeks 2–4) and Phase 3 (weeks 7–10), about 60 days, which fits inside 90.
- **Spend guardrails:**
  - Budget alerts at $50, $150 and $250. Alerts don't stop spending on their own.
  - Spot/preemptible GPU instances.
  - An auto-shutdown script on every VM, and a weekly check for idle disks and IPs.

**Rough split of the $300** (estimates):

| Use | Phase | Estimate |
|---|---|---|
| Gemini on Vertex, several configurations on about 1–2k clips | 1 | ≤ $20 |
| Google Speech-to-Text on the benchmark clips | 1 | a few $ |
| GPU fine-tuning (L4 24 GB, spot where possible): Whisper LoRA, and optionally an open audio LLM or 7–8B LoRA | 3 | $60–120 |
| Storage and egress for training audio subsets (never the full 320 GB) | 3 | ≤ $10 |
| Reserve for mistakes and reruns | — | ~$150 |

**What this changes in the plan.** Fine-tuning the speech model on S2L human audio becomes a real Phase 3 experiment
rather than "optional". It tests directly whether adapting the acoustics fixes the misheard-symbol errors found in Phase 2.
The 7–8B LoRA, which is tight on the M5, can also run in the cloud instead.

## 9. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Frontier models already nearly solve the task, so custom models matter less | Medium–high | That's a publishable finding in itself. Pivot weight to on-device performance, correction UX and real dictation |
| The benchmark (read speech, TTS) doesn't reflect real use | High | RealDictation-100 (Phase 2) |
| CER penalizes correct but differently written LaTeX | High | Render-equivalent metric. Report several metrics |
| API models change mid-project | High | Pin versions and dates. Store raw outputs |
| Licensing | Low–medium | Dataset is CC BY 4.0, so commercial use is fine with attribution. Check each base model's license and each API's terms on training with outputs |
| Privacy of voice recordings (GDPR) | Medium | Local-first by default. Consent forms. Collect no more data than needed |
| Scope creep | High | Gates between phases. Out-of-scope list above |
| Phase 3 doesn't beat prompting | Medium | Still a valid result. Ship the best prompting setup locally |

## 10. What this can become

- **University project:** it has a clear research question, a reproducible benchmark, a system and a user study. It fits a semester project or a thesis. It can be framed as research (RQ1–4) or as a product or venture (RQ5 plus market validation).
- **Publication:** results for frontier models on S2L, plus a real-dictation test set, could make a workshop paper or an arXiv technical report. Accessibility venues and speech/NLP workshops are both options.
- **Open-source credibility:** a public leaderboard that others can submit to.
- **Product:** an accessibility-first tool. Institutional buyers include university disability offices and assistive-technology funding programs. A freemium plugin for Overleaf or Obsidian could follow.
- **Collaboration:** the S2L authors published their code and data openly, so sharing results with them is an easy way to get feedback.

## 11. Open decisions

1. **Main goal:** research (paper or thesis), product (venture) or portfolio? This decides whether Phase 3 or Phases 4–5 get more weight.
2. **Time and deadline:** hours per week, and any semester or submission date.
3. **Budget and API keys:** is about $50–150 acceptable, and which providers do you have keys for?
4. **Language:** English only for v1?
5. **University context:** is there a course or supervisor, and what format, ethics or IP rules apply?

## 12. References

- Korzh et al., *Speech-to-LaTeX: New Models and Datasets for Converting Spoken Equations and Sentences*, ICLR 2026. [arXiv:2508.03542](https://arxiv.org/abs/2508.03542) · [code](https://github.com/dkorzh10/speech2latex) · [dataset](https://huggingface.co/datasets/marsianin500/Speech2Latex)
- Hyeon et al., *MathSpeech*, AAAI 2025. [arXiv:2412.15655](https://arxiv.org/abs/2412.15655)
- *MathBridge* (spoken-English ↔ LaTeX text pairs). [arXiv:2408.07081](https://arxiv.org/abs/2408.07081)
- Prior tools: [SayTeX](https://pypi.org/project/saytex/), [WhiLa](https://pypi.org/project/whila/), [Mathfly](https://github.com/mrob95/mathfly), [MathVoice (Obsidian)](https://www.obsidianstats.com/plugins/mathvoice)
