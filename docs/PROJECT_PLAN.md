# LaTeX-Dictate — Project Plan

**Status:** v2. Decisions are locked (§11). No code yet. This document decides what gets built.

**One line:** speak mathematics, get correct LaTeX, using **open models that run on a laptop**.

| | Decision |
|---|---|
| Goals | **Research** (new, reproducible findings) and **portfolio** (a public, polished, demo-able project) |
| Budget | **$0 out of pocket.** Open-weight models only. The Google Cloud $300 trial covers the one closed reference model. Free Kaggle GPUs cover training |
| Language | English |
| Setup | Independent and solo, with AI pair-programming. Work happens in free time, so the plan uses milestones, not weeks |
| Hardware | MacBook with Apple M5, 16 GB unified memory |

---

## 1. Problem

General-purpose dictation is now very good for prose and very bad for maths. Say "the integral from zero to infinity of
e to the minus x squared dx" and you get the words back, or a garbled mix of symbols. Typing LaTeX is slow, and for
people with RSI, motor impairments or low vision it can be impossible.

**Why now:**

- **A dataset now exists.** *Speech-to-LaTeX* (ICLR 2026) released the first large open dataset for this task, licensed **CC BY 4.0**. It has 66k human and 571k synthetic recordings.
- **The published results use old models.** The state of the art comes from small, older open models: about 27% character error rate (CER) on equations and about 40% on maths inside sentences.
- **Newer open models haven't been tested on it.** Open speech models improved a lot in 2025–26 (Whisper-turbo, Parakeet, Qwen3-ASR, Voxtral, Granite Speech, Canary-Qwen), and none of them has been published on this benchmark.
- **Laptops can run them.** Apple Silicon and MLX now run these models locally, so offline, private maths dictation is realistic.

## 2. Goal and principles

**Goal:** find out how far *free, open* models are from "maths dictation just works." Close that gap with a model that
runs on a 16 GB laptop, and publish everything so anyone can reproduce it and build on it.

**Principles:**

- **Open by default.** Every headline result is reproducible with open weights on a laptop or a free GPU. The one closed model, Gemini, appears only as a labelled *reference point*.
- **Measure before building.** Every engineering choice comes from a benchmark number.
- **Local first.** Voice is personal data, and on-device is the actual product idea.
- **Reproducible and public.** Pinned model versions, one command per experiment, raw outputs stored, results published.

## 3. Research questions

| # | Question | Hypothesis | If true | If false |
|---|---|---|---|---|
| RQ1 | Do current **open** models, with no training, beat the paper's fine-tuned state of the art? How far are they from a closed frontier model (Gemini)? | Yes. The best open cascade beats the paper's ~27% CER. A gap to Gemini remains. | Headline finding: "newer open models already beat the published state of the art." Effort shifts to closing the open–closed gap. | Fine-tuning (RQ3) becomes the core contribution. |
| RQ2 | What kinds of errors remain? | Most are about structure or scope (fractions, exponents, brackets), not misheard symbols. | Train the text step, and design for disambiguation. | Train the speech model (acoustic adaptation). |
| RQ3 | Can a fine-tuned **on-device** open model match the closed reference? | Yes. A LoRA-tuned model of ≤4B parameters gets within 5 CER points of Gemini, at under 1.5 s on the M5. | "You don't need the cloud for this." | Quantify the gap, and say which component limits it. |
| RQ4 | Do benchmark results hold up for natural, unscripted dictation? | No. The benchmark is people reading prepared phrasings, and natural speech is noticeably harder. | Our natural-speech test set becomes a key contribution. | The S2L benchmark is enough on its own. |

A usability pilot with a few friends is a nice-to-have for the demo, not a research question.

## 4. Scope

**In scope:**

- English.
- Two tasks:
  - **Equations:** one spoken formula becomes LaTeX.
  - **Sentences:** prose with maths in it becomes text with inline `$…$`.
- Open-weight speech and language models, plus Gemini as a closed reference paid by the trial credit.
- A benchmark harness, an error taxonomy, a natural-speech test set, a fine-tuned on-device model, a demo app and a public write-up.

**Out of scope:**

- Paid APIs, such as Claude or OpenAI.
- Product or market validation, and a formal user study.
- Other languages.
- Editing whole documents by voice.
- Mobile apps.
- Training a speech model from scratch, or downloading the full 320 GB dataset.

## 5. Approach

### 5.1 The systems we compare

**Test data:** samples of the S2L test splits, English only. They are streamed, never fully downloaded, and human and TTS recordings are reported separately.

There are two stages:

1. **Speech recognition (ASR):** audio → transcript.
2. **Text step:** transcript → LaTeX.

A "cascade" chains the two. An "end-to-end" model goes from audio straight to LaTeX.

| Family | Candidates. Exact versions are pinned in M0, because the field moves monthly | Runs on |
|---|---|---|
| Floor | Whisper-large-v3-turbo transcript, with no text step | M5 (MLX) |
| Paper reproduction | The dataset's own Whisper transcripts → the authors' released Qwen2.5-math-1.5B S2L model | M5 |
| Open speech recognition | Whisper-large-v3-turbo, Parakeet-TDT-0.6B-v2, Qwen3-ASR. Also Granite Speech and Canary-Qwen-2.5B, which currently top the Open ASR Leaderboard | M5 (MLX), or Kaggle when there's no MLX port |
| Open text step, no training | Current best open 3–8B instruct models, 4-bit. Both plain prompting and retrieved few-shot examples | M5 (MLX) |
| Open end-to-end audio LLM | Voxtral Mini 3B, and an open "omni" model if one runs on MLX | M5 (MLX) |
| **Oracle** | The dataset's correct pronunciation text → text step. This isolates speech errors from LaTeX errors | M5 |
| Closed reference | Gemini on Vertex AI (audio in → LaTeX). Optionally Google Speech-to-Text as a speech step | Google Cloud credit |
| **Ours** (M3) | A LoRA-tuned text step, and a LoRA-tuned Whisper or Voxtral | Text model on the M5, speech model on Kaggle |

**Experimental design.** Testing every speech model with every text model is wasteful. We use a *cross* design instead:

1. Pick the best text step on the oracle transcripts.
2. Pair it with every speech model.
3. Pair the best speech model with every text step.

This keeps the matrix at about 12–15 runs instead of 50+.

### 5.2 Metrics

- **CER on normalized LaTeX.** This is the headline number. It uses the paper's own normalizer and evaluation code (MIT-licensed), so it's directly comparable to their results.
- **Token error rate** and **exact match** after normalization.
- **Render rate:** the share of outputs that compile in KaTeX.
- **Render-equivalent match (stretch):** both outputs render to the same normalized MathML. This credits correct LaTeX that is written differently.
- **Latency:** p50 and p95 from the end of speech. Also peak RAM, and whether the system works offline.
- **Statistics:** bootstrap 95% confidence intervals, and paired comparisons between systems on the same clips.

### 5.3 Train the text step on the laptop, the speech step on free GPUs

The S2L training split already includes a Whisper transcript for every clip, paired with its LaTeX. So the text step
can be LoRA-trained on **text only, on the M5**, without touching the audio.

Adapting the *speech* model (Whisper or Voxtral) to maths vocabulary needs a GPU and a few thousand to tens of
thousands of audio clips. That runs on **Kaggle's free GPUs**: about 30 h/week on T4 or P100, no card needed. The
Google Cloud credit is the fallback if Kaggle's hardware isn't enough.

## 6. Milestones

The plan uses milestones rather than weeks, because time is free time and AI pair-programming compresses the coding.

**Where the time actually goes:**

| Gets much faster with AI help | Doesn't get faster |
|---|---|
| Harness code, scripts, analysis, plots, write-up drafts | **Compute.** Model runs take machine hours, so they run overnight |
| | **People.** Recording other speakers depends on their availability |
| | **Your verification.** Spot-checking error labels and every claim before publishing |
| | **Waiting on platforms.** Kaggle weekly quota, Google Cloud setup |

| Milestone | What gets done | Your sessions | Machine time | Done when |
|---|---|---|---|---|
| **M0 Feasibility** | Stream test-split samples (check access, columns, sizes, audio format). Run 50 clips through 3 systems. Measure RAM and latency on the M5. Pin model versions. Record 20 of your own formulas | 1 | about 1 h | The pipeline works end to end. Local inference uses ≤12 GB RAM and ≤3 s per formula. First RQ1 numbers exist |
| **M1 Benchmark** | Harness with per-stage caching and resumable runs. About 500 human + 250 TTS equations and 300 human sentences. The cross-design matrix. Reproduce the paper's numbers | 1–2 | 1–2 overnight runs | Reproduction is within ±3 CER points of the paper. The RQ1 table has confidence intervals |
| **M2 Errors + natural speech** | AI-assisted labelling of about 200 errors, verified by you. **NaturalDictation-100:** 100–200 unscripted formulas from 5–10 speakers, with consent forms | 2–3 | small | Taxonomy done (RQ2). Gap between scripted and natural speech measured (RQ4) |
| **M3 On-device model** | Improve the text step: prompting, then retrieved few-shot examples, then LoRA on the M5. Speech-model LoRA on Kaggle. Each step is kept only if it helps | 3–5 | several training runs, each a few hours | RQ3 answered. Best model published with a model card |
| **M4 Demo** | Push-to-talk → LaTeX → live KaTeX preview → paste into any editor. A few voice corrections ("undo", "make that a fraction"). Python backend with a small web UI | 2–3 | — | A 2-minute demo video, recorded live |
| **M5 Write-up + release** | Technical report. Public leaderboard. Model and natural-speech set on Hugging Face. Polished README | 2–3 | — | Everything public and reproducible from the README |

## 7. Targets

These are provisional. We revise them after M0, once real numbers exist.

| Area | Minimum | Target | Stretch |
|---|---|---|---|
| Harness validity | Paper baseline reproduced within ±3 CER pts | — | — |
| Best **open, untrained** system, human English equations | Report it | Beats the paper (<27% CER) | ≤15% |
| Best **open, fine-tuned on-device** system, same test set | Beats the best untrained system | ≤15% CER | ≤10% |
| On-device vs. Gemini reference | Gap reported | Within 5 pts | Matches or beats it |
| Sentences (equation CER) | Report it | ≤30% | ≤20% |
| Render rate | ≥95% | ≥98% | ≥99.5% |
| Local latency (p95, M5) | ≤3 s | ≤1.5 s | ≤0.8 s |
| Local peak RAM | ≤12 GB | ≤8 GB | ≤5 GB |
| Natural-speech set | n ≥ 100 from ≥5 speakers | n ≥ 200 from ≥8 speakers | Published on Hugging Face |

**Portfolio checklist:**

- [ ] One-command reproduction
- [ ] Public leaderboard
- [ ] Model card on Hugging Face
- [ ] Demo video
- [ ] Technical report
- [ ] Clean README with a results figure

## 8. Resources: the $0 plan

| Resource | Used for | Cost |
|---|---|---|
| **M5, 16 GB** | All inference. Text-step LoRA (1.5–4B parameters). Data preparation and analysis | $0 |
| **Kaggle notebooks** (about 30 GPU-h/week, T4/P100) | Speech-model LoRA. Models with no MLX port | $0, no card needed |
| **Google Cloud trial** ($300, 90 days) | Gemini reference on Vertex AI. Optional Google Speech-to-Text. A GPU only if Kaggle isn't enough | $0 within the credit |
| **Hugging Face** (free account) | Dataset access. Hosting the model, the natural-speech set and the leaderboard | $0 |
| **GitHub** | Code, report, project page | $0 |

**What fits on the M5:**

| Work | Fits? | Notes |
|---|---|---|
| Benchmark audio sample (about 1–2k clips) | Yes, under 1 GB | Streamed. The 320 GB dataset is never fully downloaded |
| Whisper-turbo / Parakeet inference (MLX) | Yes, about 1–2 GB | |
| 3–8B LLM inference, 4-bit | Yes, about 2–5 GB | |
| A speech model and an LLM loaded together | Yes, about 7–8 GB | Stages can also run one after the other |
| Voxtral Mini 3B (end-to-end), 4-bit | Yes, about 3 GB | |
| LoRA on a 1.5–4B text model | Yes | Text-only data, a few hours |
| QLoRA on a 7–8B text model | Tight | Batch size 1, short sequences. Run on Kaggle instead if needed |
| Speech-model fine-tuning | No | Kaggle |

**On using the SSD as extra RAM:** macOS swaps to the SSD automatically. That's fine for occasional spikes during
inference, but training while swapping is 10–100× slower and wears the drive, so the plan stays within RAM. Keep about
25 GB of free disk for model weights and caches.

### 8.1 Google Cloud trial: how we use it

These terms are from community guides. Check them on Google's free-trial page before signing up.

- **Start it at M1, not before.** The 90-day clock starts at signup.
- **Use Vertex AI.** Gemini calls through Vertex AI draw on the credit. Calls through an AI Studio API key reportedly don't.
- **Don't upgrade unless you must.** GPUs require upgrading to a paid account, and after that any spend beyond the credit goes to your card. Kaggle comes first for GPUs, so the account can likely **stay on the trial and never be charged.**
- **If you do upgrade:**
  - Budget alerts at $50, $150 and $250. Alerts don't stop spending on their own.
  - Spot GPU instances only.
  - An auto-shutdown script on every VM.
  - New accounts may need to request GPU quota, which can take days or be denied.

**Expected spend:**

| Use | Estimate |
|---|---|
| Gemini reference (a few prompt variants on about 1–2k clips, equations + sentences) | ≤ $30 |
| Google Speech-to-Text | a few $ |
| Everything else | $0. The rest of the credit is spare |

## 9. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Open untrained models already nearly solve the task | Medium | Publishable in itself. Focus moves to on-device performance, natural speech and the demo |
| The benchmark (read speech, TTS) doesn't reflect real use | High | NaturalDictation-100 (M2) |
| CER penalizes correct but differently written LaTeX | High | Render-equivalent metric. Report several metrics |
| A model has no MLX port, or the port is buggy | Medium | Run it on Kaggle. Note which models are actually on-device-ready, which is itself useful information |
| Kaggle quota or hardware changes | Low–medium | Google Cloud credit as fallback |
| Card charges after a Google Cloud upgrade | Low, with guardrails | Stay on the trial unless a GPU is unavoidable. Use alerts and auto-shutdown |
| Model versions change mid-project | High | Pin versions and dates. Store raw outputs |
| Licensing | Low | Dataset is CC BY 4.0, which allows any use with attribution. Record each model's license in the results table. Prefer permissively licensed bases (Apache-2.0 / MIT) for the released model |
| **Voice recordings of other people** | Medium | GDPR still applies to you as an individual once you publish data. Written consent, collect no more than needed (no names in files), and a clear opt-out |
| Scope creep | High | Each milestone has a "done when". Out-of-scope list above |
| Overclaiming results | Medium | Confidence intervals, paired tests, and claims only about the tested setup. Limitations section in the report |

## 10. Outputs

**Research:**

- **Technical report** with the RQ1–RQ4 findings.
  - Posted on GitHub Pages and/or as a Hugging Face blog post.
  - An arXiv preprint is possible. First-time submitters may need an endorsement.
  - A workshop paper is a possible later step.
- **Public leaderboard** for spoken maths → LaTeX, open to submissions.
- **Open artifacts on Hugging Face:**
  - the fine-tuned on-device model, with a model card;
  - NaturalDictation-100, if consent allows publishing it.

**Portfolio:**

- A repo that reproduces everything from the README.
- A results figure.
- A 2-minute demo video.
- A live demo, such as a Hugging Face Space.

**Outreach:** share results with the S2L authors. Their code and data are open, and they're the natural audience and possible collaborators.

**Later, not now:** an accessibility-focused product, a university project or thesis, or other languages. Each would reuse everything above.

## 11. Decisions

**Locked:**

- **Goals:** research + portfolio.
- **Budget:** $0 out of pocket. Open models, the Google Cloud trial credit, and Kaggle.
- **Language:** English.
- **Setup:** independent, no university involvement.
- **Timeline:** milestone-based.

**Still open.** None of these block M0:

1. **Accounts:** Hugging Face (needed in M0, in case the dataset requires login), Kaggle (M3) and Google Cloud (M1).
2. **Speakers for NaturalDictation:** can you recruit 5–10 people (friends, classmates) for about 15 minutes each?
3. **Repo license:** MIT or Apache-2.0. Recommendation: **Apache-2.0**, which matches most of the open models involved.

## 12. References

- Korzh et al., *Speech-to-LaTeX: New Models and Datasets for Converting Spoken Equations and Sentences*, ICLR 2026. [arXiv:2508.03542](https://arxiv.org/abs/2508.03542) · [code](https://github.com/dkorzh10/speech2latex) · [dataset](https://huggingface.co/datasets/marsianin500/Speech2Latex)
- Hyeon et al., *MathSpeech*, AAAI 2025. [arXiv:2412.15655](https://arxiv.org/abs/2412.15655)
- *MathBridge* (spoken-English ↔ LaTeX text pairs). [arXiv:2408.07081](https://arxiv.org/abs/2408.07081)
- [Open ASR Leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard) · [mlx-audio](https://github.com/Blaizzy/mlx-audio) · [mlx-lm](https://github.com/ml-explore/mlx-lm)
- Prior tools: [SayTeX](https://pypi.org/project/saytex/), [WhiLa](https://pypi.org/project/whila/), [Mathfly](https://github.com/mrob95/mathfly), [MathVoice (Obsidian)](https://www.obsidianstats.com/plugins/mathvoice)
