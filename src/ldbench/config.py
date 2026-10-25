"""Benchmark configuration (TOML) and the model lock file."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

TASKS = ("equations", "sentences")

# ASR specs of the form "column:<name>" read a transcript straight from the manifest
# (e.g. the dataset's precomputed Whisper output, or the ground-truth pronunciation).
COLUMN_PREFIX = "column:"


@dataclass
class ModelCfg:
    name: str
    kind: str
    repo: str
    revision: str | None = None
    options: dict = field(default_factory=dict)


@dataclass
class SplitCfg:
    name: str
    source: str  # "hf" | "paper-samples" | "local"
    task: str
    hf_split: str | None = None
    quota: dict[str, int] = field(default_factory=dict)
    path: str | None = None


@dataclass
class SystemCfg:
    name: str
    asr: str | None = None
    text: dict[str, str] | None = None  # task -> model name
    e2e: str | None = None
    prompt: str = "zero-shot"
    max_tokens: int = 256
    # Split-then-convert for sentences: this LLM marks the maths spans, which the text model converts.
    segmenter: str | None = None

    def text_model_for(self, task: str) -> str | None:
        if self.text is None:
            return None
        return self.text.get(task, self.text.get("all"))


@dataclass
class Config:
    path: Path
    run_name: str
    seed: int
    data_dir: Path
    runs_dir: Path
    dataset_repo: str
    language: str
    max_per_row_group: int
    splits: dict[str, SplitCfg]
    models: dict[str, ModelCfg]
    systems: dict[str, SystemCfg]
    gates: dict[str, float]

    @property
    def run_dir(self) -> Path:
        return self.runs_dir / self.run_name

    def split_data_dir(self, split: SplitCfg) -> Path:
        if split.source == "local":
            return Path(split.path)
        return self.data_dir / self.run_name / split.name

    @property
    def lock_path(self) -> Path:
        return self.path.with_suffix(".lock.json")

    def pinned_revision(self, model: ModelCfg) -> str | None:
        """Explicit revision from the config wins; otherwise use the lock file if present."""
        if model.revision:
            return model.revision
        if self.lock_path.exists():
            lock = json.loads(self.lock_path.read_text())
            entry = lock.get("models", {}).get(model.name)
            if entry and entry.get("repo") == model.repo:
                return entry.get("sha")
        return None


def _resolve(base: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base / p)


def load_config(path: str | Path) -> Config:
    path = Path(path).resolve()
    raw = tomllib.loads(path.read_text())
    # Relative paths in the config are relative to the repository root (the config's parent dir's parent).
    root = path.parent.parent

    models = {
        name: ModelCfg(
            name=name,
            kind=m["kind"],
            repo=m["repo"],
            revision=m.get("revision"),
            options=m.get("options", {}),
        )
        for name, m in raw.get("models", {}).items()
    }

    splits: dict[str, SplitCfg] = {}
    for s in raw.get("splits", []):
        split = SplitCfg(
            name=s["name"],
            source=s["source"],
            task=s["task"],
            hf_split=s.get("hf_split"),
            quota=dict(s.get("quota", {})),
            path=str(_resolve(root, s["path"])) if s.get("path") else None,
        )
        if split.task not in TASKS:
            raise ValueError(f"split {split.name}: unknown task {split.task!r}")
        if split.source == "local" and not split.path:
            raise ValueError(f"split {split.name}: local splits need a path")
        splits[split.name] = split

    systems: dict[str, SystemCfg] = {}
    for s in raw.get("systems", []):
        text = s.get("text")
        if isinstance(text, str):
            text = {"all": text}
        system = SystemCfg(
            name=s["name"],
            asr=s.get("asr"),
            text=text,
            e2e=s.get("e2e"),
            prompt=s.get("prompt", "zero-shot"),
            max_tokens=int(s.get("max_tokens", 256)),
            segmenter=s.get("segmenter"),
        )
        _validate_system(system, models)
        systems[system.name] = system

    ds = raw.get("dataset", {})
    return Config(
        path=path,
        run_name=raw["run_name"],
        seed=int(raw.get("seed", 0)),
        data_dir=_resolve(root, raw.get("data_dir", "data")),
        runs_dir=_resolve(root, raw.get("runs_dir", "runs")),
        dataset_repo=ds.get("repo", "marsianin500/Speech2Latex"),
        language=ds.get("language", "eng"),
        max_per_row_group=int(ds.get("max_per_row_group", 4)),
        splits=splits,
        models=models,
        systems=systems,
        gates=dict(raw.get("gates", {})),
    )


def _validate_system(system: SystemCfg, models: dict[str, ModelCfg]) -> None:
    if bool(system.e2e) == bool(system.asr):
        raise ValueError(f"system {system.name}: set exactly one of 'asr' or 'e2e'")
    if system.e2e and system.e2e not in models:
        raise ValueError(f"system {system.name}: unknown e2e model {system.e2e!r}")
    if system.asr and not system.asr.startswith(COLUMN_PREFIX) and system.asr not in models:
        raise ValueError(f"system {system.name}: unknown asr model {system.asr!r}")
    for model_name in (system.text or {}).values():
        if model_name not in models:
            raise ValueError(f"system {system.name}: unknown text model {model_name!r}")
    if system.segmenter and system.segmenter not in models:
        raise ValueError(f"system {system.name}: unknown segmenter model {system.segmenter!r}")
    if system.segmenter and not system.asr:
        raise ValueError(f"system {system.name}: a segmenter needs an 'asr' transcript")
    if system.prompt not in ("zero-shot", "paper"):
        raise ValueError(f"system {system.name}: unknown prompt style {system.prompt!r}")
