"""Run one system over the configured splits, with per-stage caching and timing.

Layout under ``runs/<run_name>/``:

- ``<split>/asr/<asr_model>.jsonl``   transcripts, shared by every system using that ASR model
- ``<split>/pred/<system>.jsonl``     final predictions with per-item latency
- ``meta/<system>.json``              load times, peak memory per stage, model pins, environment

Runs are resumable: items already present in a cache file are skipped.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from tqdm import tqdm

from . import backends
from .backends import ASR_KINDS, E2E_KINDS, TEXT_KINDS
from .backends import mlx as mlx_mem
from .config import COLUMN_PREFIX, Config, ModelCfg, SplitCfg, SystemCfg
from .data import read_manifest
from .postprocess import clean_output
from .prompts import e2e_prompt, text_messages
from .sysinfo import environment

# Files fetched from model repos. Covers MLX checkpoints and transformers-format repos.
ALLOW_PATTERNS = [
    "*.json", "*.safetensors", "*.npz", "*.py", "*.model", "*.tiktoken", "*.txt", "*.jinja", "tokenizer*",
]


def slug(name: str) -> str:
    return name.replace("/", "_").replace(":", "_").replace("@", "_at_")


def resolve_model(cfg: Config, model: ModelCfg) -> tuple[str, str]:
    """Download (or reuse) a pinned snapshot; returns (local_path, commit_sha).

    A repo that is an existing local directory (e.g. your own fine-tuned model) is used as is.
    """
    if Path(model.repo).expanduser().is_dir():
        return str(Path(model.repo).expanduser()), "local"

    from huggingface_hub import snapshot_download

    path = snapshot_download(
        model.repo, revision=cfg.pinned_revision(model), allow_patterns=ALLOW_PATTERNS
    )
    return path, Path(path).name


def _read_jsonl(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["id"]] = rec
    return out


def _append(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class ModelPool:
    """Loads each model once per process and records load time, peak memory and pinned SHA."""

    def __init__(self, cfg: Config, meta: dict):
        self.cfg = cfg
        self.meta = meta
        self.live: dict[str, object] = {}

    def get(self, name: str, table: dict):
        if name in self.live:
            return self.live[name]
        model = self.cfg.models[name]
        local_path, sha = resolve_model(self.cfg, model)
        mlx_mem.reset_peak_memory()
        t0 = time.perf_counter()
        obj = backends.create(table, model, local_path)
        stage = self.meta["models"].setdefault(name, {})
        stage.update({"repo": model.repo, "sha": sha, "kind": model.kind,
                      "load_s": round(time.perf_counter() - t0, 2)})
        self.live[name] = obj
        return obj

    def record_peak(self, name: str) -> None:
        peak = mlx_mem.peak_memory_gb()
        if peak is not None:
            stage = self.meta["models"].setdefault(name, {})
            stage["peak_memory_gb"] = round(max(stage.get("peak_memory_gb", 0.0), peak), 3)

    def release(self, name: str) -> None:
        self.live.pop(name, None)
        mlx_mem.free_memory()


def _timed(fn, *args):
    t0 = time.perf_counter()
    out = fn(*args)
    return out, time.perf_counter() - t0


def run_asr_stage(cfg: Config, pool: ModelPool, split: SplitCfg, asr: str, items: list[dict],
                  split_dir: Path) -> dict[str, dict]:
    """Transcripts for every item: from a manifest column, the cache, or by running the model."""
    if asr.startswith(COLUMN_PREFIX):
        col = asr[len(COLUMN_PREFIX):]
        return {i["id"]: {"id": i["id"], "text": i.get(col) or "", "sec": None} for i in items}

    cache_path = cfg.run_dir / split.name / "asr" / f"{slug(asr)}.jsonl"
    cache = _read_jsonl(cache_path)
    todo = [i for i in items if i["id"] not in cache]
    if todo:
        model = pool.get(asr, ASR_KINDS)
        model.transcribe(str(split_dir / todo[0]["audio"]))  # warm-up, not timed
        for item in tqdm(todo, desc=f"{split.name}: {asr}", unit="clip"):
            text, sec = _timed(model.transcribe, str(split_dir / item["audio"]))
            rec = {"id": item["id"], "text": text, "sec": round(sec, 4)}
            _append(cache_path, rec)
            cache[item["id"]] = rec
        pool.record_peak(asr)
    return cache


def applicable(system: SystemCfg, split: SplitCfg, items: list[dict]) -> str | None:
    """Reason the system cannot run on this split, or None."""
    if not items:
        return "no items (run `ldb fetch` / record audio first)"
    if system.asr and system.asr.startswith(COLUMN_PREFIX):
        col = system.asr[len(COLUMN_PREFIX):]
        if not any(i.get(col) for i in items):
            return f"split has no '{col}' column"
    if system.asr and system.text is not None and system.text_model_for(split.task) is None:
        return f"no text model for task '{split.task}'"
    return None


def clear_system(cfg: Config, system_name: str) -> list[Path]:
    """Delete a system's predictions, its meta file and the transcripts of its ASR model."""
    system = cfg.systems[system_name]
    paths = [cfg.run_dir / "meta" / f"{slug(system_name)}.json"]
    for split in cfg.splits:
        paths.append(cfg.run_dir / split / "pred" / f"{slug(system_name)}.jsonl")
        if system.asr and not system.asr.startswith(COLUMN_PREFIX):
            paths.append(cfg.run_dir / split / "asr" / f"{slug(system.asr)}.jsonl")
    removed = [p for p in paths if p.exists()]
    for p in removed:
        p.unlink()
    return removed


def run_system(cfg: Config, system_name: str, split_names: list[str] | None = None,
               limit: int | None = None) -> dict:
    system = cfg.systems[system_name]
    meta_path = cfg.run_dir / "meta" / f"{slug(system_name)}.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta.update({"system": system_name, "environment": environment()})
    meta.setdefault("models", {})
    meta.setdefault("splits", {})
    pool = ModelPool(cfg, meta)

    for split_name in split_names or list(cfg.splits):
        split = cfg.splits[split_name]
        split_dir = cfg.split_data_dir(split)
        items = read_manifest(split_dir)[:limit] if limit else read_manifest(split_dir)
        reason = applicable(system, split, items)
        if reason:
            meta["splits"][split.name] = {"skipped": reason}
            continue

        pred_path = cfg.run_dir / split.name / "pred" / f"{slug(system_name)}.jsonl"
        done = _read_jsonl(pred_path)
        todo = [i for i in items if i["id"] not in done]

        if system.e2e:
            _run_e2e(pool, system, split, split_dir, todo, pred_path)
        else:
            transcripts = run_asr_stage(cfg, pool, split, system.asr, items, split_dir)
            text_model = system.text_model_for(split.task)
            if text_model is None:
                for item in todo:
                    t = transcripts[item["id"]]
                    _append(pred_path, {"id": item["id"], "pred": clean_output(t["text"], split.task),
                                        "raw": t["text"], "transcript": t["text"], "asr_s": t["sec"],
                                        "gen_s": None if t["sec"] is None else 0.0, "total_s": t["sec"]})
            else:
                if not system.asr.startswith(COLUMN_PREFIX):
                    pool.release(system.asr)  # measure each model's peak separately
                _run_text(pool, system, split, text_model, todo, transcripts, pred_path)
        meta["splits"][split.name] = {"items": len(items), "new_predictions": len(todo)}

    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


def _run_text(pool: ModelPool, system: SystemCfg, split: SplitCfg, model_name: str,
              todo: list[dict], transcripts: dict[str, dict], pred_path: Path) -> None:
    if not todo:
        return
    model = pool.get(model_name, TEXT_KINDS)
    first = transcripts[todo[0]["id"]]["text"]
    model.generate(text_messages(system.prompt, split.task, first), system.max_tokens)  # warm-up
    for item in tqdm(todo, desc=f"{split.name}: {system.name}", unit="item"):
        t = transcripts[item["id"]]
        raw, sec = _timed(model.generate, text_messages(system.prompt, split.task, t["text"]),
                          system.max_tokens)
        asr_s = t["sec"]
        _append(pred_path, {
            "id": item["id"], "pred": clean_output(raw, split.task), "raw": raw,
            "transcript": t["text"], "asr_s": asr_s, "gen_s": round(sec, 4),
            "total_s": round(sec + (asr_s or 0.0), 4) if asr_s is not None else None,
        })
    pool.record_peak(model_name)


def _run_e2e(pool: ModelPool, system: SystemCfg, split: SplitCfg, split_dir: Path,
             todo: list[dict], pred_path: Path) -> None:
    if not todo:
        return
    model = pool.get(system.e2e, E2E_KINDS)
    prompt = e2e_prompt(split.task)
    model.generate(str(split_dir / todo[0]["audio"]), prompt, system.max_tokens)  # warm-up
    for item in tqdm(todo, desc=f"{split.name}: {system.name}", unit="clip"):
        raw, sec = _timed(model.generate, str(split_dir / item["audio"]), prompt, system.max_tokens)
        _append(pred_path, {"id": item["id"], "pred": clean_output(raw, split.task), "raw": raw,
                            "transcript": None, "asr_s": None, "gen_s": round(sec, 4),
                            "total_s": round(sec, 4)})
    pool.record_peak(system.e2e)
