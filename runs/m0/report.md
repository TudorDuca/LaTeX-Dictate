# Run report: m0

Machine: Apple M5, 17.2 GB, macOS 26.6.2, Python 3.12.14. Generated 2026-10-25T12:27:30+00:00.

CER is corpus-level on normalized LaTeX (see `src/ldbench/metrics.py`), against the dataset's raw LaTeX (`sentence`); *vs norm. ref* repeats it against the dataset's `sentence_normalized` column. *Median* is the median per-item CER and *Capped* caps each item's CER at 100%; both are robust to a single runaway output or refusal. For sentences, *prose WER* is the word error rate on the text outside $...$ (does the system keep what was said?). Not yet directly comparable with the paper's published numbers (different normalizer and sample).

## Gate checks: NOT PASSED

| System | Check | Result | Detail |
|---|---|---|---|
| whisper-raw | pipeline runs end to end | ✅ | equations: 50 items, 100.0% non-empty, sentences: 10 items, 100.0% non-empty, own: 20 items, 100.0% non-empty |
| whisper-raw | peak memory ≤ 12 GB | ✅ | 2.19 GB |
| whisper-raw | p95 latency ≤ 3.0 s (equations) | ✅ | 0.42 s |
| paper@dataset-asr | pipeline runs end to end | ✅ | equations: 50 items, 100.0% non-empty, sentences: 10 items, 100.0% non-empty |
| paper@whisper-turbo | pipeline runs end to end | ✅ | equations: 50 items, 100.0% non-empty, sentences: 10 items, 100.0% non-empty, own: 20 items, 100.0% non-empty |
| paper@whisper-turbo | peak memory ≤ 12 GB | ✅ | 8.45 GB |
| paper@whisper-turbo | p95 latency ≤ 3.0 s (equations) | ✅ | 1.25 s |
| qwen3-4b@whisper-turbo | pipeline runs end to end | ✅ | equations: 50 items, 98.0% non-empty, sentences: 10 items, 100.0% non-empty, own: 20 items, 100.0% non-empty |
| qwen3-4b@whisper-turbo | peak memory ≤ 12 GB | ✅ | 8.07 GB |
| qwen3-4b@whisper-turbo | p95 latency ≤ 3.0 s (equations) | ✅ | 1.20 s |
| qwen3-4b@oracle | pipeline runs end to end | ✅ | equations: 50 items, 100.0% non-empty, sentences: 10 items, 100.0% non-empty |
| qwen2-audio@e2e | pipeline runs end to end | ✅ | equations: 50 items, 100.0% non-empty, sentences: 10 items, 100.0% non-empty, own: 20 items, 100.0% non-empty |
| qwen2-audio@e2e | peak memory ≤ 12 GB | ✅ | 7.56 GB |
| qwen2-audio@e2e | p95 latency ≤ 3.0 s (equations) | ✅ | 2.04 s |
| split@dataset-asr | pipeline runs end to end | ✅ | sentences: 10 items, 100.0% non-empty |
| split@whisper-turbo | pipeline runs end to end | ✅ | sentences: 10 items, 100.0% non-empty |
| split@whisper-turbo | peak memory ≤ 12 GB | ❌ | 14.33 GB |

## equations (equations, 50 items)

| System | n | CER (95% CI) | Median | Capped | vs norm. ref | CER human | CER tts | Exact | Renders | Latency p50 / p95 (s) | Peak mem (GB) | Load (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| whisper-raw | 50 | 153.1% (132.5%–177.1%) | 162.1% | 93.5% | 147.7% | 146.1% | 181.0% | 0.0% | 100.0% | 0.37 / 0.42 | 2.19 | 1.3 |
| paper@dataset-asr | 50 | 50.8% (21.0%–106.0%) | 20.5% | 26.4% | 45.9% | 43.9% | 78.2% | 32.0% | 100.0% | 0.48 / 0.99* | 6.26 | 1.3 |
| paper@whisper-turbo | 50 | 23.5% (16.3%–32.1%) | 14.7% | 22.5% | 19.4% | 18.7% | 42.5% | 36.0% | 100.0% | 0.85 / 1.20 | 8.44 | 2.6 |
| qwen3-4b@whisper-turbo | 50 | 75.8% (46.3%–119.3%) | 42.7% | 49.5% | 76.6% | 50.7% | 175.4% | 16.0% | 98.0% | 0.82 / 1.20 | 8.07 | 3.6 |
| qwen3-4b@oracle | 50 | 36.8% (24.8%–48.1%) | 25.6% | 36.5% | 38.6% | 33.2% | 51.2% | 32.0% | 100.0% | 0.42 / 0.66* | 5.89 | 2.2 |
| qwen2-audio@e2e | 50 | 82.6% (74.6%–93.1%) | 82.4% | 77.2% | 82.8% | 84.0% | 77.0% | 4.0% | 94.0% | 1.47 / 2.02 | 7.56 | 4.2 |
| split@dataset-asr | skipped: no text model for task 'equations' | | | | | | | | | | | |
| split@whisper-turbo | skipped: no text model for task 'equations' | | | | | | | | | | | |

\* latency of the text step only (the transcript comes from the dataset).

## sentences (sentences, 10 items)

| System | n | equation CER (95% CI) | Median | Capped | vs norm. ref | full-text CER | prose WER | equation CER human | Exact | Renders | Latency p50 / p95 (s) | Peak mem (GB) | Load (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| whisper-raw | 10 | 100.0% (100.0%–100.0%) | 100.0% | 100.0% | 100.0% | 19.2% | 42.6% | 100.0% | 0.0% | — | 0.40 / 0.50 | 2.19 | 1.3 |
| paper@dataset-asr | 10 | 60.4% (36.4%–75.4%) | 46.6% | 60.4% | 51.0% | 15.9% | 12.6% | 60.4% | 10.0% | 95.0% | 0.82 / 4.38* | 6.26 | 0.9 |
| paper@whisper-turbo | 10 | 59.7% (32.6%–74.9%) | 46.6% | 59.7% | 51.0% | 22.9% | 21.9% | 59.7% | 20.0% | 94.7% | 1.22 / 4.96 | 8.45 | 2.2 |
| qwen3-4b@whisper-turbo | 10 | 50.7% (20.0%–70.8%) | 19.6% | 50.7% | 52.3% | 14.0% | 16.4% | 50.7% | 30.0% | 100.0% | 1.08 / 1.66 | 8.07 | 3.6 |
| qwen3-4b@oracle | 10 | 39.6% (4.9%–60.0%) | 0.0% | 39.6% | 45.6% | 10.8% | 9.8% | 39.6% | 60.0% | 100.0% | 0.70 / 1.18* | 5.89 | 2.2 |
| qwen2-audio@e2e | 10 | 123.9% (79.1%–226.2%) | 95.0% | 82.8% | 120.8% | 32.5% | 30.6% | 123.9% | 20.0% | 100.0% | 2.51 / 3.27 | 7.56 | 4.2 |
| split@dataset-asr | 10 | 132.1% (76.1%–280.0%) | 192.3% | 71.6% | 124.2% | 27.1% | 23.0% | 132.1% | 0.0% | 100.0% | 1.52 / 2.61* | 12.14 | 3.5 |
| split@whisper-turbo | 10 | 120.9% (75.2%–240.0%) | 192.3% | 71.6% | 114.1% | 24.4% | 21.9% | 120.9% | 0.0% | 100.0% | 1.96 / 2.99 | 14.33 | 4.9 |

\* latency of the text step only (the transcript comes from the dataset).

## own (equations, 20 items)

| System | n | CER (95% CI) | Median | Capped | vs norm. ref | CER own | Exact | Renders | Latency p50 / p95 (s) | Peak mem (GB) | Load (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| whisper-raw | 20 | 136.5% (117.3%–163.3%) | 139.4% | 95.0% | 136.5% | 136.5% | 0.0% | 100.0% | 0.37 / 0.41 | 2.19 | 1.3 |
| paper@dataset-asr | skipped: split has no 'whisper_text' column | | | | | | | | | | |
| paper@whisper-turbo | 20 | 12.5% (6.2%–19.3%) | 0.0% | 12.5% | 12.5% | 12.5% | 60.0% | 100.0% | 0.94 / 1.25 | 8.44 | 2.6 |
| qwen3-4b@whisper-turbo | 20 | 31.4% (16.9%–46.6%) | 18.5% | 31.4% | 31.4% | 31.4% | 30.0% | 100.0% | 0.89 / 1.18 | 8.07 | 3.6 |
| qwen3-4b@oracle | skipped: split has no 'pronunciation' column | | | | | | | | | | |
| qwen2-audio@e2e | 20 | 56.7% (42.1%–69.3%) | 58.3% | 56.5% | 56.7% | 56.7% | 10.0% | 90.0% | 1.56 / 2.04 | 7.56 | 4.2 |
| split@dataset-asr | skipped: split has no 'whisper_text' column | | | | | | | | | | |
| split@whisper-turbo | skipped: no text model for task 'equations' | | | | | | | | | | |

\* latency of the text step only (the transcript comes from the dataset).

## Data

### equations

```json
{
  "split": "equations",
  "method": "parquet",
  "files": [
    "equations_test-00000-of-00001.parquet"
  ],
  "rows_total": 2880,
  "rows_by_language_group": {
    "eng/human": 1515,
    "eng/tts": 1230,
    "ru/human": 45,
    "ru/tts": 90
  },
  "sampled": {
    "human": 40,
    "tts": 10
  },
  "quota": {
    "human": 40,
    "tts": 10
  },
  "row_groups_downloaded": 25,
  "audio_formats": {
    "wav": 50
  },
  "sample_rates": {
    "48000": 37,
    "44100": 2,
    "16000": 1,
    "24000": 10
  },
  "mean_duration_s": 7.22,
  "columns": [
    "spk: string",
    "language: string",
    "sentence_id: int64",
    "is_tts: int64",
    "pronunciation: string",
    "whisper_text: string",
    "sentence: string",
    "audio_path: struct<bytes: binary, path: string>",
    "formula_info: string",
    "count_formula_symbols: double",
    "count_formula_symbols_strates: string",
    "__index_level_0__: int64",
    "sentence_normalized: string"
  ],
  "audio_column": "audio_path",
  "repo": "marsianin500/Speech2Latex",
  "hf_split": "equations_test",
  "revision": "main"
}
```

### sentences

```json
{
  "split": "sentences",
  "method": "parquet",
  "files": [
    "sentences_test-00000-of-00002.parquet",
    "sentences_test-00001-of-00002.parquet"
  ],
  "rows_total": 2850,
  "rows_by_language_group": {
    "eng/human": 772,
    "eng/tts": 2078
  },
  "sampled": {
    "human": 10
  },
  "quota": {
    "human": 10
  },
  "row_groups_downloaded": 9,
  "audio_formats": {
    "wav": 10
  },
  "sample_rates": {
    "48000": 8,
    "44100": 2
  },
  "mean_duration_s": 12.083,
  "columns": [
    "spk: string",
    "language: string",
    "sentence_id: int64",
    "is_tts: int64",
    "pronunciation: string",
    "whisper_text: string",
    "sentence: string",
    "audio_path: struct<bytes: binary, path: string>",
    "formula_info: string",
    "count_formula_symbols: double",
    "count_formula_symbols_strates: string",
    "__index_level_0__: int64",
    "sentence_normalized: string"
  ],
  "audio_column": "audio_path",
  "repo": "marsianin500/Speech2Latex",
  "hf_split": "sentences_test",
  "revision": "main"
}
```

### own

```json
{
  "split": "own",
  "method": "local",
  "sampled": {
    "own": 20
  },
  "missing_recordings": [],
  "mean_duration_s": 8.638
}
```

## Models

| Model | Kind | Repo @ commit | Load (s) | Peak mem (GB) |
|---|---|---|---|---|
| paper-eq | mlx-lm | `marsianin500/Qwen2.5-math-1.5B-instruct-equations_multilingual_mix@3a085dcbcd` | 1.3 | 6.26 |
| paper-sent | mlx-lm | `marsianin500/Qwen2.5-math-1.5B-instruct-sentences_eng_mix@94bc54a177` | 0.9 | 6.26 |
| qwen2-audio | mlx-audio-chat | `mlx-community/Qwen2-Audio-7B-Instruct-4bit@c655700026` | 4.2 | 7.56 |
| qwen3-4b | mlx-lm | `mlx-community/Qwen3-4B-Instruct-2507-4bit@50d427756c` | 2.2 | 5.89 |
| whisper-turbo | mlx-whisper | `mlx-community/whisper-large-v3-turbo@a4aaeec063` | 1.3 | 2.19 |
