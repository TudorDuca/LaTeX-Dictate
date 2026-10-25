# M0 results: feasibility

**Date:** 2026-10-25.
**Machine:** MacBook Pro, Apple M5, 16 GB, macOS 26.6.
**Raw outputs:** [`runs/m0/report.md`](../runs/m0/report.md) (full tables), [`runs/m0/examples.md`](../runs/m0/examples.md) (side-by-side outputs), `runs/m0/*/pred/*.jsonl` (every prediction).
**Exact clips used:** `data/m0/*/manifest.jsonl`.
**Model pins:** [`configs/m0.lock.json`](../configs/m0.lock.json).

## Verdict: gate passed

Every system ran end to end on the laptop and stayed within the M0 limits. That covers the open models and the
paper's released model, with open models doing both speech recognition (ASR) and LaTeX conversion.

| Gate (plan §6) | Result |
|---|---|
| Pipeline runs end to end | ✅ 6/6 systems, 100% coverage. One system left 1 of 50 outputs empty |
| Peak memory ≤ 12 GB | ✅ Worst case 8.4 GB (Whisper + the paper's model, both loaded) |
| p95 latency ≤ 3 s per formula | ✅ Worst case 2.0 s (Qwen2-Audio). Whisper → small LLM takes 1.2 s; Whisper alone takes 0.4 s |
| First RQ1 numbers | ✅ Below |

The data path also works: seeded sampling straight from the dataset's parquet files. It downloaded 25 chunks for 50 clips, not the 320 GB dataset.

## Results

**Sample:** 40 human-recorded and 10 TTS English equations from the S2L test split, plus 20 formulas recorded by the author.

**Metric:**
- CER on normalized LaTeX against the dataset's raw LaTeX. Lower is better.
- *Capped* limits each clip's error at 100%, so one runaway output can't dominate a 50-clip average.

| System | Equations CER (95% CI) | Capped | Median per clip | Exact | Own recordings CER (Exact) | p95 latency | Peak mem |
|---|---|---|---|---|---|---|---|
| Whisper-turbo, no conversion (floor) | 153% | 94% | 162% | 0% | 137% (0%) | 0.4 s | 2.2 GB |
| Paper's 1.5B model ← dataset's Whisper transcripts | 51% (21–106) | 26% | 21% | 32% | — | 1.0 s\* | 6.3 GB |
| **Paper's 1.5B model ← our Whisper-turbo** | **24% (16–32)** | **23%** | **15%** | **36%** | **12.5% (60%)** | 1.2 s | 8.4 GB |
| Qwen3-4B-Instruct (4-bit), zero-shot ← Whisper-turbo | 76% (46–119) | 50% | 43% | 16% | 31% (30%) | 1.2 s | 4.8 GB |
| Qwen3-4B, zero-shot ← *correct pronunciation* (oracle) | 37% (25–48) | 37% | 26% | 32% | — | 0.7 s\* | 2.6 GB |
| Qwen2-Audio-7B (4-bit), zero-shot, audio in → LaTeX | 83% (75–93) | 77% | 82% | 4% | 57% (10%) | 2.0 s | 7.6 GB |

\* Text step only; the transcript comes from the dataset.

**Breakdowns:**
- **Human vs TTS clips:** the best system scores 18.7% on human clips and 42.5% on TTS clips.
- **Sentences (10 items):** these are reported in `runs/m0/report.md`, but n = 10 is too few to read anything into.

**Dataset facts measured here** (not published elsewhere):

| Split | Total | English, human | English, TTS | Russian |
|---|---|---|---|---|
| `equations_test` | 2,880 | 1,515 | 1,230 | 135 |
| `sentences_test` | 2,850 | 772 | 2,078 | none |

- Audio is WAV at 16–48 kHz. Clips are about 7 s on average for equations and 12 s for sentences.

## Findings

1. **Fine-tuning matters far more than model size or type.** The paper's 1.5B fine-tuned model has a capped CER of 23%. A 4B general instruct model gets 50%, and a 7B audio LLM gets 77%. Both of those ran with no fine-tuning.
2. **For untrained models, the conversion step is the bottleneck, not speech recognition.** Given the *correct* pronunciation, Qwen3-4B still scores 37%. Its errors on human clips are mostly about format and convention, and less about maths structure:
   - it writes Unicode instead of LaTeX commands (`ζ^(-1/2)`, `≡`, `∂T_xx/∂x`, `c₁`);
   - it leaves spoken words untranslated (`A_{0} of Z_{i} is isomorphic to …`);
   - it keeps or drops the prose around a formula differently from the reference;
   - genuine structure errors also occur, for example `p - 1 !` instead of `(p-1)!`.

   A prompt and a few in-context examples may fix much of the first three. M1 tests that on a dev split.
3. **Untrained models fail in ways a fine-tuned model doesn't.**
   - Qwen3-4B sometimes *explains* instead of converting. On two garbled TTS clips it wrote "The transcript is incomplete…", and it sometimes copies the spoken words through as `\text{...}`.
   - Qwen2-Audio often writes the spoken words instead of LaTeX, for example `\textit{a supercript 2 f of x is less than or equal to …}`.
4. **The paper's model has a runaway failure mode.** "capital R C 1000,000" set off an endless `1,0,0,0,…` repetition loop. That single clip is the whole gap between its two input variants: 51% vs 24% CER, but a median per clip of 21% vs 15%. Our Whisper-turbo transcripts are nearly identical to the dataset's own, so there's no evidence yet that better speech recognition helps.
5. **Some TTS clips don't match their reference.** For example, the reference `\tau_{age}=60` was heard as "how long sum aj equals 16" by both Whisper versions. The cascades do much worse on TTS clips than on human ones (best system: 18.7% vs 42.5%). Human-recorded clips should carry the headline numbers, and TTS reliability needs a measured audit.
   The references are also inconsistent about spoken statements. "Wilson's theorem states that if p is prime, then…" maps to the formula only. "The general solution to … is …" keeps `\text{ is }` and both formulas. No system can match both conventions, so this sets a floor on achievable CER.
6. **Natural dictation was *not* worse in this small test.** The author's 20 recordings scored 12.5% CER with 60% exact matches using the paper's model. That compares with 18.7% on the dataset's human clips. But see the limitations below.
7. **The scoring choice matters:**
   - The dataset's normalized LaTeX uses `\\` as a space marker (`\csc\\x`) and adds grouping braces (`\lim_{{x\to 4}}`). The paper's model reproduces those conventions.
   - The harness now treats them as equivalent and scores against the raw LaTeX by default. With the normalized reference, the paper's model looks better (19.4% vs 23.5%) while the other systems barely change.
   - Reports show both, and M1 adds the paper's own normalizer for direct comparability.

## What this means for the research questions

- **RQ1** (do untrained open models beat the paper?): **early answer: no, at least at 4–7B.** Per the plan's decision table, fine-tuning (M3) becomes the core contribution. M1 still tests larger open text models and the Gemini reference before closing RQ1.
- **RQ2** (what kinds of errors remain?): the early signal is that conversion errors outweigh misheard symbols (finding 2). For untrained models these are mostly format and convention errors. That supports putting the effort into the transcript → LaTeX step on the laptop, through prompting first and then fine-tuning. The full taxonomy is M2.
- **RQ3** (on-device): **promising.** The best system already runs in 1.2 s within 8.4 GB. The paper's 1.5B checkpoint peaks at 6.3 GB, which suggests 32-bit weights. 4-bit quantization should bring it to roughly 1–2 GB. That's an M1/M3 check.
- **RQ4** (natural speech): not supported yet, but the evidence is weak. See the limitations.

## Limitations

- **Small sample.** With 50 equations, the confidence intervals are ±8–40 points, so differences between the top two systems aren't significant yet. Ten sentences can't support any conclusion.
- **Our own set is easy and one person.** The 20 formulas are textbook classics (Bayes' rule, the limit definition of the derivative, and so on), read by a single speaker. The S2L training data probably contains near-identical formulas, so they may flatter the paper's model. NaturalDictation (M2) needs more speakers and less canonical formulas.
- **Provisional metric.** The headline numbers use this harness's normalizer, not the paper's, so they aren't directly comparable with its published ~27% CER, although they're in the same range.
- **Prompts not tuned.** Zero-shot prompts were written once, before seeing any data. They're left as-is here on purpose, so that no prompt is tuned against the test set.

## Changes for M1

1. **Comparability:** add the paper's normalizer and evaluation script as a second scorer. Run the reproduction gate: within ±3 CER points of the published number.
2. **Dev split:** sample a dev set from `equations_train` and `sentences_train` for all prompt and decoding changes. The test sample stays untouched.
3. **Decoding guards:** a repetition penalty and/or a `max_tokens` scaled to transcript length, applied equally to every system.
4. **Prompts,** tuned on dev only: always answer with a best-guess LaTeX formula, never an explanation.
5. **Scale up:** 500 human + 250 TTS equations and 300 human sentences. Paired bootstrap tests between systems. Report human results as the headline.
6. **Wider system matrix:**
   - larger open text models (an 8–9B instruct model, 4-bit);
   - other open ASR models (Parakeet-TDT, Qwen3-ASR);
   - quantized versions of the paper's model;
   - Gemini via Vertex AI as the closed reference, which starts the Google Cloud trial.
7. **TTS audit:** estimate how many TTS clips don't match their reference, by checking a random 50 by ear or against the oracle, before using TTS numbers for any claim.
