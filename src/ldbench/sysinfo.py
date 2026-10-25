"""Environment description, pre-flight checks (`ldb doctor`) and model pinning."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

PACKAGES = ("ldbench", "mlx", "mlx-lm", "mlx-whisper", "mlx-audio", "huggingface_hub", "pyarrow", "rapidfuzz")


def _sysctl(key: str) -> str | None:
    try:
        return subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def environment() -> dict:
    mem = _sysctl("hw.memsize")
    versions = {}
    for p in PACKAGES:
        try:
            versions[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            versions[p] = None
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "chip": _sysctl("machdep.cpu.brand_string") or platform.processor(),
        "memory_gb": round(int(mem) / 1e9, 1) if mem and mem.isdigit() else None,
        "macos": platform.mac_ver()[0] or None,
        "python": sys.version.split()[0],
        "packages": versions,
    }


def doctor(cfg) -> tuple[list[tuple[str, bool, str]], dict]:
    """Checks for running the config on this machine; also resolves model SHAs for the lock file."""
    from huggingface_hub import HfApi

    from .katex import katex_available

    env = environment()
    checks: list[tuple[str, bool, str]] = []
    checks.append(("Apple Silicon (arm64 macOS)",
                   env["machine"] == "arm64" and bool(env["macos"]),
                   f"{env['chip']} / macOS {env['macos']}"))
    checks.append(("Unified memory", bool(env["memory_gb"]), f"{env['memory_gb']} GB"))
    free_gb = shutil.disk_usage(cfg.path.parent).free / 1e9
    checks.append(("Free disk ≥ 25 GB (model weights + data)", free_gb >= 25, f"{free_gb:.0f} GB free"))
    checks.append(("ffmpeg on PATH (audio decoding)", shutil.which("ffmpeg") is not None,
                   "brew install ffmpeg" if not shutil.which("ffmpeg") else "ok"))
    missing = [p for p in ("mlx", "mlx-lm", "mlx-whisper", "mlx-audio") if not env["packages"].get(p)]
    checks.append(("MLX backends installed", not missing,
                   "ok" if not missing else f"missing {missing}: uv pip install -e '.[mac]'"))
    checks.append(("KaTeX checker (optional, render-rate metric)", katex_available(),
                   "ok" if katex_available() else "cd tools/katex && npm install"))

    api = HfApi()
    try:
        who = api.whoami()
        checks.append(("Hugging Face login", True, who.get("name", "ok")))
    except Exception:  # noqa: BLE001
        checks.append(("Hugging Face login (optional unless the dataset is gated)", False, "hf auth login"))

    needs_dataset = any(s.source == "hf" for s in cfg.splits.values())
    if needs_dataset:
        try:
            info = api.dataset_info(cfg.dataset_repo)
            gated = getattr(info, "gated", False)
            checks.append((f"Dataset {cfg.dataset_repo} reachable", True,
                           f"sha {info.sha[:10]}" + (f", gated={gated}" if gated else "")))
        except Exception as e:  # noqa: BLE001
            checks.append((f"Dataset {cfg.dataset_repo} reachable", False, type(e).__name__ + ": " + str(e)[:120]))

    lock = {"created": env["timestamp"], "models": {}}
    for name, model in cfg.models.items():
        if Path(model.repo).expanduser().is_dir():
            checks.append((f"Model {name}", True, f"local directory {model.repo}"))
            continue
        try:
            info = api.model_info(model.repo, revision=cfg.pinned_revision(model))
            lock["models"][name] = {"repo": model.repo, "sha": info.sha}
            checks.append((f"Model {name}", True, f"{model.repo}@{info.sha[:10]}"))
        except Exception as e:  # noqa: BLE001
            checks.append((f"Model {name}", False, f"{model.repo}: {type(e).__name__}"))
    return checks, lock


def write_lock(cfg, lock: dict) -> None:
    """Keep existing pins; add new models. Delete the lock file to re-pin to latest."""
    existing = json.loads(cfg.lock_path.read_text()) if cfg.lock_path.exists() else {"models": {}}
    for name, entry in lock["models"].items():
        old = existing["models"].get(name)
        if not old or old.get("repo") != entry["repo"]:
            existing["models"][name] = entry
    existing.setdefault("created", lock["created"])
    cfg.lock_path.write_text(json.dumps(existing, indent=2) + "\n")
