"""Command line: ldb doctor | fetch | record | run | score | all | dictate."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .config import load_config

DEFAULT_CONFIG = "configs/m0.toml"


def cmd_doctor(args) -> int:
    from .sysinfo import doctor, write_lock

    cfg = load_config(args.config)
    checks, lock = doctor(cfg)
    width = max(len(c[0]) for c in checks)
    for name, ok, detail in checks:
        print(f"  {'✅' if ok else '❌'}  {name.ljust(width)}  {detail}")
    write_lock(cfg, lock)
    print(f"\nModel pins written to {cfg.lock_path} (commit it to make runs reproducible).")
    hard = [c for c in checks if not c[1] and c[0].startswith(("Apple Silicon", "MLX backends", "Model ", "Dataset"))]
    return 1 if hard else 0


def cmd_fetch(args) -> int:
    from .data import build_local_manifest, fetch_hf_split, fetch_paper_samples, write_stats

    cfg = load_config(args.config)
    for split in cfg.splits.values():
        if args.split and split.name not in args.split:
            continue
        split_dir = cfg.split_data_dir(split)
        if split.source == "local":
            stats = build_local_manifest(split_dir)
        elif (split_dir / "manifest.jsonl").exists() and not args.force:
            print(f"{split.name}: already fetched ({split_dir}); use --force to refetch")
            continue
        elif split.source == "hf":
            stats = fetch_hf_split(cfg.dataset_repo, split.hf_split, split_dir, split.name, split.task,
                                   cfg.language, split.quota, cfg.seed, cfg.max_per_row_group, args.method)
        elif split.source == "paper-samples":
            stats = fetch_paper_samples(split_dir, split.hf_split, split.task, cfg.language)
        else:
            raise ValueError(f"unknown source {split.source!r}")
        write_stats(split_dir, stats)
        print(f"{split.name}: {stats.get('sampled')} -> {split_dir}")
        if stats.get("missing_recordings"):
            print(f"  not recorded yet: {', '.join(stats['missing_recordings'])}  (run `ldb record`)")
    return 0


def cmd_record(args) -> int:
    from .record import list_devices, record

    if args.list_devices:
        print(list_devices())
        return 0
    stats = record(Path(args.dir), only=args.only, redo=args.redo, device=args.device)
    print(f"\n{stats['sampled']['own']} recordings in manifest; missing: {stats['missing_recordings'] or 'none'}")
    return 0


def cmd_run(args) -> int:
    from .runner import clear_system, run_system

    cfg = load_config(args.config)
    if args.fresh:
        clear_system(cfg, args.system)
    meta = run_system(cfg, args.system, args.split, args.limit)
    infos = meta["splits"]
    for split, info in infos.items():
        if "skipped" in info:
            print(f"  {split}: skipped ({info['skipped']})")
        else:
            cached = info["items"] - info["new_predictions"]
            print(f"  {split}: {info['items']} items, {info['new_predictions']} new"
                  + (f", {cached} already done" if cached else ""))
    if infos and all(i.get("new_predictions", 0) == 0 for i in infos.values() if "skipped" not in i):
        print(f"  nothing new to run: results are cached under {cfg.run_dir}/ "
              "(use --fresh to recompute this system)")
    return 0


def cmd_dictate(args) -> int:
    from .dictate import main as dictate_main

    cfg = load_config(args.config)
    dictate_main(cfg, args.system, args.task, args.mode, args.hotkey, args.wrap, args.paste,
                 args.device, args.save_audio, not args.no_sound)
    return 0


def cmd_score(args) -> int:
    from .report import compute, write_report

    cfg = load_config(args.config)
    path = write_report(cfg, compute(cfg))
    print(f"Report: {path}")
    return 0


def cmd_all(args) -> int:
    """Fetch data, run every system in its own process (clean memory measurement), then score."""
    cfg = load_config(args.config)
    cmd_fetch(argparse.Namespace(config=args.config, split=None, force=False, method="auto"))
    systems = args.system or list(cfg.systems)
    if args.fresh:
        from .runner import clear_system

        for name in systems:  # clear everything up front so shared transcripts are recomputed once
            clear_system(cfg, name)
        print(f"Cleared cached results for: {', '.join(systems)}")
    failed = []
    for name in systems:
        print(f"\n=== {name} ===", flush=True)
        cmd = [sys.executable, "-m", "ldbench.cli", "run", "--config", args.config, "--system", name]
        if args.limit:
            cmd += ["--limit", str(args.limit)]
        if subprocess.run(cmd).returncode != 0:
            failed.append(name)
            print(f"!!! {name} failed; continuing with the other systems", flush=True)
    cmd_score(args)
    if failed:
        print(f"Failed systems: {', '.join(failed)}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ldb", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    def with_config(sp):
        sp.add_argument("--config", default=DEFAULT_CONFIG, help=f"benchmark config (default {DEFAULT_CONFIG})")
        return sp

    with_config(sub.add_parser("doctor", help="check this machine, dataset access, and pin model versions"))

    sp = with_config(sub.add_parser("fetch", help="sample the configured splits to data/"))
    sp.add_argument("--split", action="append", help="only these splits (repeatable)")
    sp.add_argument("--force", action="store_true", help="refetch even if a manifest exists")
    sp.add_argument("--method", choices=["auto", "parquet", "stream"], default="auto")

    sp = sub.add_parser("record", help="record your own formulas with the microphone")
    sp.add_argument("--dir", default="data/own")
    sp.add_argument("--only", action="append", help="only these formula ids (repeatable)")
    sp.add_argument("--redo", action="store_true", help="re-record existing files")
    sp.add_argument("--device", help="input device index or name (see --list-devices)")
    sp.add_argument("--list-devices", action="store_true", help="list audio devices and exit")

    sp = with_config(sub.add_parser("run", help="run one system"))
    sp.add_argument("--system", required=True)
    sp.add_argument("--split", action="append")
    sp.add_argument("--limit", type=int, help="only the first N items per split (debugging)")
    sp.add_argument("--fresh", action="store_true", help="delete this system's cached results first")

    with_config(sub.add_parser("score", help="score predictions and write the report"))

    sp = with_config(sub.add_parser("dictate", help="push-to-talk: speak maths, get LaTeX in any app"))
    sp.add_argument("--system", default="paper@whisper-turbo", help="any non-oracle system from the config")
    sp.add_argument("--task", choices=["equations", "sentences"], default="equations")
    sp.add_argument("--mode", choices=["hold", "toggle", "terminal"], default="hold",
                    help="hold the hotkey while speaking (default), press to start/stop, or Enter in the terminal")
    sp.add_argument("--hotkey", help="pynput syntax; default <alt_r> (right Option) for hold, "
                                     "<ctrl>+<alt>+m for toggle")
    sp.add_argument("--paste", action="store_true", help="also paste into the focused app (Cmd+V)")
    sp.add_argument("--wrap", choices=["none", "inline", "display"], default="none",
                    help="wrap the output in $...$ (inline) or \\[...\\] (display)")
    sp.add_argument("--device", help="input device index or name (see ldb record --list-devices)")
    sp.add_argument("--save-audio", action="store_true", help="keep each take under data/dictations/audio/")
    sp.add_argument("--no-sound", action="store_true", help="no start/stop sounds")

    sp = with_config(sub.add_parser("all", help="fetch + run every system + score"))
    sp.add_argument("--system", action="append", help="only these systems (repeatable)")
    sp.add_argument("--limit", type=int)
    sp.add_argument("--fresh", action="store_true", help="delete cached results and recompute everything")

    args = p.parse_args(argv)
    handler = {"doctor": cmd_doctor, "fetch": cmd_fetch, "record": cmd_record, "run": cmd_run,
               "score": cmd_score, "all": cmd_all, "dictate": cmd_dictate}[args.command]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
