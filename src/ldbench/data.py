"""Benchmark data: sampling the Speech2Latex test splits, the paper's sample clips, and local recordings.

Every split ends up as a directory with ``manifest.jsonl`` (one item per clip) and an ``audio/`` folder.
Manifest items carry: id, audio (path relative to the split dir), group ("human" | "tts" | "own"),
language, target (reference LaTeX), and, where available, pronunciation and whisper_text.
"""

from __future__ import annotations

import csv
import json
import random
import re
import urllib.request
import wave
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Callable, Iterable

MANIFEST = "manifest.jsonl"
STATS = "stats.json"

# Pinned commit of github.com/dkorzh10/speech2latex whose sample clips we use for smoke tests.
PAPER_REPO_COMMIT = "d43b4d4f51e4c4071492534a31fb79d0e19b4631"
PAPER_RAW = f"https://raw.githubusercontent.com/dkorzh10/speech2latex/{PAPER_REPO_COMMIT}"

# Text columns copied from the dataset when present.
TEXT_COLUMNS = ("sentence", "sentence_normalized", "pronunciation", "whisper_text")


# --------------------------------------------------------------------------- manifest I/O


def read_manifest(split_dir: Path) -> list[dict]:
    path = Path(split_dir) / MANIFEST
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_manifest(split_dir: Path, items: list[dict]) -> None:
    split_dir = Path(split_dir)
    split_dir.mkdir(parents=True, exist_ok=True)
    with open(split_dir / MANIFEST, "w") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def strip_math_delimiters(s: str) -> str:
    s = s.strip()
    for left, right in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$")):
        if s.startswith(left) and s.endswith(right) and len(s) >= len(left) + len(right):
            return s[len(left) : len(s) - len(right)].strip()
    return s


def pick_target(row: dict, task: str) -> str:
    """Reference LaTeX: the dataset's normalized form when present (the paper evaluates against it)."""
    target = (row.get("sentence_normalized") or row.get("sentence") or "").strip()
    return strip_math_delimiters(target) if task == "equations" else target


# --------------------------------------------------------------------------- audio helpers


def sniff_audio_ext(data: bytes, path_hint: str | None = None) -> str:
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:4] == b"fLaC":
        return "flac"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if path_hint and "." in path_hint:
        return path_hint.rsplit(".", 1)[-1].lower()
    return "bin"


def audio_info(path: Path) -> dict:
    """Duration and format for WAV files (stdlib only); other formats report what is known."""
    if path.suffix.lower() != ".wav":
        return {"format": path.suffix.lstrip(".")}
    try:
        with wave.open(str(path), "rb") as w:
            frame_bytes = w.getnchannels() * w.getsampwidth()
            # Some TTS clips have a streaming-style header with a bogus (maximal) frame count;
            # never claim more frames than the file can hold.
            frames = min(w.getnframes(), max(0, path.stat().st_size - 44) // max(1, frame_bytes))
            return {
                "format": "wav",
                "sample_rate": w.getframerate(),
                "channels": w.getnchannels(),
                "duration_s": round(frames / float(w.getframerate()), 3),
            }
    except (wave.Error, EOFError):
        return {"format": "wav"}


def _write_audio(split_dir: Path, item_id: str, audio: dict) -> dict:
    data = audio.get("bytes")
    if not data:
        raise ValueError(f"{item_id}: audio cell has no embedded bytes")
    ext = sniff_audio_ext(data, audio.get("path"))
    rel = Path("audio") / f"{item_id}.{ext}"
    out = split_dir / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return {"audio": str(rel), **audio_info(out)}


# --------------------------------------------------------------------------- Speech2Latex (HF parquet)


@dataclass
class RowRef:
    file_idx: int
    row_group: int
    row_in_group: int
    meta: dict

    @property
    def group(self) -> str:
        return "tts" if _truthy(self.meta.get("is_tts")) else "human"


def _truthy(v) -> bool:
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes")
    return bool(v)


def find_audio_column(schema) -> str:
    """The HF Audio feature is stored in parquet as struct<bytes: binary, path: string>."""
    import pyarrow as pa

    for f in schema:
        if pa.types.is_struct(f.type) and {"bytes", "path"} <= {c.name for c in f.type}:
            return f.name
    raise ValueError("no audio column (struct<bytes, path>) found in parquet schema")


def scan_parquet(
    files: list[str], open_fn: Callable[[str], BinaryIO]
) -> tuple[list[RowRef], dict, str]:
    """Read every non-audio column of every row (cheap: text only) and remember where each row lives."""
    import pyarrow.parquet as pq

    rows: list[RowRef] = []
    columns: list[str] | None = None
    audio_col: str | None = None
    for file_idx, name in enumerate(files):
        pf = pq.ParquetFile(open_fn(name))
        arrow_schema = pf.schema_arrow
        audio_col = audio_col or find_audio_column(arrow_schema)
        meta_cols = [f.name for f in arrow_schema if f.name != audio_col]
        if columns is None:
            columns = [f"{f.name}: {f.type}" for f in arrow_schema]
        for rg in range(pf.metadata.num_row_groups):
            table = pf.read_row_group(rg, columns=meta_cols)
            for i, meta in enumerate(table.to_pylist()):
                rows.append(RowRef(file_idx, rg, i, meta))
    schema_info = {"columns": columns or [], "audio_column": audio_col}
    return rows, schema_info, audio_col


def select_rows(
    rows: list[RowRef],
    language: str,
    quota: dict[str, int],
    seed: int,
    max_per_row_group: int,
) -> dict[str, list[RowRef]]:
    """Seeded random sample per group, spread across row groups so we download few, varied chunks."""
    rng = random.Random(seed)
    by_group: dict[str, list[RowRef]] = defaultdict(list)
    for r in rows:
        if str(r.meta.get("language", "")).lower() == language.lower():
            by_group[r.group].append(r)

    chosen: dict[str, list[RowRef]] = {}
    per_rg: Counter = Counter()  # shared across groups: caps what we download per row group
    for group, n in quota.items():
        candidates = by_group.get(group, [])[:]
        rng.shuffle(candidates)
        picked: list[RowRef] = []
        for r in candidates:  # first pass: respect the per-row-group cap
            key = (r.file_idx, r.row_group)
            if per_rg[key] < max_per_row_group:
                picked.append(r)
                per_rg[key] += 1
                if len(picked) == n:
                    break
        if len(picked) < n:  # second pass: relax the cap if the group is small
            seen = {id(r) for r in picked}
            picked += [r for r in candidates if id(r) not in seen][: n - len(picked)]
        chosen[group] = picked
    return chosen


def fetch_parquet_sample(
    files: list[str],
    open_fn: Callable[[str], BinaryIO],
    split_dir: Path,
    split_name: str,
    task: str,
    language: str,
    quota: dict[str, int],
    seed: int,
    max_per_row_group: int,
) -> dict:
    import pyarrow.parquet as pq

    rows, schema_info, audio_col = scan_parquet(files, open_fn)
    lang_group_counts = Counter(
        f"{str(r.meta.get('language', '?')).lower()}/{r.group}" for r in rows
    )
    chosen = select_rows(rows, language, quota, seed, max_per_row_group)

    needed: dict[tuple[int, int], list[tuple[str, RowRef]]] = defaultdict(list)
    for group, refs in chosen.items():
        for k, r in enumerate(refs):
            needed[(r.file_idx, r.row_group)].append((f"{group}_{k:04d}", r))

    split_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    open_files: dict[int, object] = {}
    for (file_idx, rg), refs in sorted(needed.items()):
        if file_idx not in open_files:
            open_files[file_idx] = pq.ParquetFile(open_fn(files[file_idx]))
        audio_cells = open_files[file_idx].read_row_group(rg, columns=[audio_col]).column(0).to_pylist()
        for item_id, r in refs:
            item = {
                "id": item_id,
                "group": r.group,
                "language": str(r.meta.get("language", "")).lower(),
                "target": pick_target(r.meta, task),
                **{c: r.meta.get(c) for c in TEXT_COLUMNS if c in r.meta},
                "source": f"{Path(files[file_idx]).name}#rg{rg}:{r.row_in_group}",
            }
            item.update(_write_audio(split_dir, item_id, audio_cells[r.row_in_group]))
            items.append(item)
    items.sort(key=lambda x: x["id"])
    write_manifest(split_dir, items)

    stats = {
        "split": split_name,
        "method": "parquet",
        "files": [Path(f).name for f in files],
        "rows_total": len(rows),
        "rows_by_language_group": dict(sorted(lang_group_counts.items())),
        "sampled": {g: len(v) for g, v in chosen.items()},
        "quota": quota,
        "row_groups_downloaded": len(needed),
        "audio_formats": dict(Counter(i.get("format") for i in items)),
        "sample_rates": dict(Counter(str(i.get("sample_rate")) for i in items)),
        "mean_duration_s": _mean([i.get("duration_s") for i in items]),
        **schema_info,
    }
    return stats


def _mean(values: Iterable) -> float | None:
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 3) if vals else None


def list_split_parquet_files(repo: str, hf_split: str) -> tuple[list[str], str | None]:
    """Parquet files for one split, from the main branch or the auto-converted parquet branch."""
    from huggingface_hub import HfApi

    api = HfApi()
    for revision in (None, "refs/convert/parquet"):
        try:
            files = api.list_repo_files(repo, repo_type="dataset", revision=revision)
        except Exception:  # noqa: BLE001 - try the next revision
            continue
        matches = sorted(
            f
            for f in files
            if f.endswith(".parquet")
            and (f"/{hf_split}/" in f"/{f}" or Path(f).name.startswith(f"{hf_split}-"))
        )
        if matches:
            return matches, revision
    return [], None


def split_row_counts(repo: str, revision: str | None, all_files: dict[str, list[str]]) -> dict:
    """Row counts per split from parquet footers only (a few KB per file)."""
    import pyarrow.parquet as pq
    from huggingface_hub import HfFileSystem

    fs = HfFileSystem()
    counts = {}
    for split, files in all_files.items():
        total = 0
        for f in files:
            with fs.open(_hf_path(repo, f, revision), "rb") as fh:
                total += pq.ParquetFile(fh).metadata.num_rows
        counts[split] = total
    return counts


def _hf_path(repo: str, file: str, revision: str | None) -> str:
    rev = f"@{revision.replace('/', '%2F')}" if revision else ""
    return f"datasets/{repo}{rev}/{file}"


def fetch_hf_split(
    repo: str,
    hf_split: str,
    split_dir: Path,
    split_name: str,
    task: str,
    language: str,
    quota: dict[str, int],
    seed: int,
    max_per_row_group: int,
    method: str = "auto",
) -> dict:
    if method in ("auto", "parquet"):
        files, revision = list_split_parquet_files(repo, hf_split)
        if files:
            from huggingface_hub import HfFileSystem

            fs = HfFileSystem()

            def open_fn(name: str) -> BinaryIO:
                return fs.open(_hf_path(repo, name, revision), "rb", block_size=2**20)

            stats = fetch_parquet_sample(
                files, open_fn, split_dir, split_name, task, language, quota, seed, max_per_row_group
            )
            stats.update({"repo": repo, "hf_split": hf_split, "revision": revision or "main"})
            return stats
        if method == "parquet":
            raise RuntimeError(f"no parquet files found for {repo}:{hf_split}")
    return fetch_streaming(repo, hf_split, split_dir, split_name, task, language, quota)


def fetch_streaming(
    repo: str,
    hf_split: str,
    split_dir: Path,
    split_name: str,
    task: str,
    language: str,
    quota: dict[str, int],
    max_scan: int = 50_000,
) -> dict:
    """Fallback: stream rows in order and keep the first matches (less random than the parquet path)."""
    import datasets

    ds = datasets.load_dataset(repo, split=hf_split, streaming=True)
    audio_col = next(
        (n for n, f in ds.features.items() if isinstance(f, datasets.Audio)), "audio_path"
    )
    ds = ds.cast_column(audio_col, datasets.Audio(decode=False))
    remaining = dict(quota)
    counters: Counter = Counter()
    items: list[dict] = []
    scanned = 0
    for row in ds:
        scanned += 1
        group = "tts" if _truthy(row.get("is_tts")) else "human"
        lang = str(row.get("language", "")).lower()
        counters[f"{lang}/{group}"] += 1
        if lang == language.lower() and remaining.get(group, 0) > 0:
            item_id = f"{group}_{quota[group] - remaining[group]:04d}"
            item = {
                "id": item_id,
                "group": group,
                "language": lang,
                "target": pick_target(row, task),
                **{c: row.get(c) for c in TEXT_COLUMNS if c in row},
                "source": f"stream:{scanned - 1}",
            }
            item.update(_write_audio(split_dir, item_id, row[audio_col]))
            items.append(item)
            remaining[group] -= 1
        if all(v <= 0 for v in remaining.values()) or scanned >= max_scan:
            break
    write_manifest(split_dir, sorted(items, key=lambda x: x["id"]))
    return {
        "split": split_name,
        "method": "stream",
        "repo": repo,
        "hf_split": hf_split,
        "rows_scanned": scanned,
        "rows_by_language_group_scanned": dict(sorted(counters.items())),
        "sampled": {g: quota[g] - remaining[g] for g in quota},
        "quota": quota,
        "audio_column": audio_col,
        "columns": list(ds.features.keys()),
        "audio_formats": dict(Counter(i.get("format") for i in items)),
        "mean_duration_s": _mean([i.get("duration_s") for i in items]),
    }


# --------------------------------------------------------------------------- paper sample clips (smoke test)


def fetch_paper_samples(split_dir: Path, hf_split: str, task: str, language: str = "eng") -> dict:
    """English sample clips shipped in the paper's GitHub repo, with their reference LaTeX.

    Only the dataset's Whisper transcript is available for these (no pronunciation column).
    """
    with urllib.request.urlopen(f"{PAPER_RAW}/docs/demo_results.json", timeout=60) as r:
        demo = json.load(r)
    items = []
    split_dir.mkdir(parents=True, exist_ok=True)
    for row in demo["results"]:
        sample_id = row["sample_id"]
        if row["split"] != hf_split or f"_{language}_" not in sample_id:
            continue
        rel = Path("audio") / f"{sample_id}.wav"
        out = split_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.exists():
            urllib.request.urlretrieve(f"{PAPER_RAW}/{row['audio_path']}", out)
        reference = row["reference_latex"].replace("\\\\", " ")
        items.append(
            {
                "id": sample_id,
                "group": "tts" if sample_id.startswith("tts") else "human",
                "language": language,
                "target": strip_math_delimiters(reference) if task == "equations" else reference,
                "whisper_text": row["whisper_transcription"],
                "audio": str(rel),
                "source": f"speech2latex@{PAPER_REPO_COMMIT[:7]}:{row['audio_path']}",
                **audio_info(out),
            }
        )
    write_manifest(split_dir, items)
    return {
        "split": hf_split,
        "method": "paper-samples",
        "sampled": dict(Counter(i["group"] for i in items)),
        "audio_formats": dict(Counter(i.get("format") for i in items)),
        "mean_duration_s": _mean([i.get("duration_s") for i in items]),
    }


# --------------------------------------------------------------------------- local recordings


FORMULAS_CSV = "formulas.csv"
ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def read_formulas(own_dir: Path) -> list[dict]:
    with open(Path(own_dir) / FORMULAS_CSV, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("id")]
    for r in rows:
        if not ID_RE.match(r["id"]):
            raise ValueError(f"bad formula id {r['id']!r} in {FORMULAS_CSV}")
    return rows


# Recordings made elsewhere (Voice Memos, QuickTime, a phone) can be dropped into audio/ as
# <id>.<ext>; they are converted to WAV with ffmpeg so every backend can read them.
OTHER_AUDIO_EXTS = (".m4a", ".mp3", ".aiff", ".aif", ".caf", ".flac", ".ogg", ".webm")


def convert_to_wav(src: Path, dst: Path) -> None:
    import shutil
    import subprocess

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(f"ffmpeg is needed to convert {src.name} to WAV (brew install ffmpeg)")
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)],
        check=True,
    )


def _local_wav(own_dir: Path, item_id: str) -> Path | None:
    wav = own_dir / "audio" / f"{item_id}.wav"
    if wav.exists():
        return wav
    for ext in OTHER_AUDIO_EXTS:
        for src in (own_dir / "audio" / f"{item_id}{ext}", own_dir / "audio" / f"{item_id}{ext.upper()}"):
            if src.exists():
                convert_to_wav(src, wav)
                return wav
    return None


def build_local_manifest(own_dir: Path) -> dict:
    """Manifest for the formulas you have recorded so far (audio/<id>.wav, or another format)."""
    own_dir = Path(own_dir)
    items = []
    missing = []
    for r in read_formulas(own_dir):
        if _local_wav(own_dir, r["id"]) is None:
            missing.append(r["id"])
            continue
        rel = Path("audio") / f"{r['id']}.wav"
        items.append(
            {
                "id": r["id"],
                "group": "own",
                "language": "eng",
                "target": strip_math_delimiters(r["latex"]),
                "difficulty": r.get("difficulty", ""),
                "audio": str(rel),
                "source": "own-recording",
                **audio_info(own_dir / rel),
            }
        )
    write_manifest(own_dir, items)
    return {
        "split": "own",
        "method": "local",
        "sampled": {"own": len(items)},
        "missing_recordings": missing,
        "mean_duration_s": _mean([i.get("duration_s") for i in items]),
    }


def write_stats(split_dir: Path, stats: dict) -> None:
    Path(split_dir).mkdir(parents=True, exist_ok=True)
    (Path(split_dir) / STATS).write_text(json.dumps(stats, indent=2, ensure_ascii=False))


def read_stats(split_dir: Path) -> dict | None:
    p = Path(split_dir) / STATS
    return json.loads(p.read_text()) if p.exists() else None
