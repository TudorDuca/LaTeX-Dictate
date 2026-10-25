"""Score predictions and write the run report (Markdown + JSON), including the M0 gate checks."""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path

from .config import COLUMN_PREFIX, Config, SystemCfg
from .data import audio_info, read_manifest, read_stats
from .katex import renders
from .metrics import (
    bootstrap_cer_ci,
    corpus_rates,
    median_item_cer,
    percentile,
    score_item,
    split_inline_math,
)
from .runner import _read_jsonl, slug

HEADLINE_VIEW = {"equations": "latex", "sentences": "formulas"}


def _fmt(x: float | None, pct: bool = False, digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return f"{100 * x:.1f}%" if pct else f"{x:.{digits}f}"


def _render_rate(preds: list[str], task: str) -> float | None:
    formulas = preds if task == "equations" else [f for p in preds for f in split_inline_math(p)[1]]
    ok = renders(formulas)
    if ok is None or not ok:
        return None
    return sum(ok) / len(ok)


def _memory(models: dict, system: SystemCfg, task: str) -> float | None:
    """Peak memory needed to run the system: ASR + text model peaks (both resident in a real app)."""
    names = [system.e2e] if system.e2e else []
    if system.asr and not system.asr.startswith(COLUMN_PREFIX):
        names.append(system.asr)
    if system.text_model_for(task):
        names.append(system.text_model_for(task))
    if system.segmenter and task == "sentences":
        names.append(system.segmenter)
    peaks = [models.get(n, {}).get("peak_memory_gb") for n in names]
    if not peaks or any(p is None for p in peaks):
        return None
    return round(sum(peaks), 2)


def _load_s(models: dict, system: SystemCfg, task: str) -> float | None:
    segmenter = system.segmenter if task == "sentences" else None
    names = [n for n in (system.e2e, system.asr, system.text_model_for(task), segmenter)
             if n and not n.startswith(COLUMN_PREFIX)]
    vals = [models.get(n, {}).get("load_s") for n in names]
    return round(sum(vals), 1) if vals and all(v is not None for v in vals) else None


def compute(cfg: Config) -> dict:
    results: dict = {"run": cfg.run_name, "splits": {}, "systems": {}}
    for system in cfg.systems.values():
        meta_path = cfg.run_dir / "meta" / f"{slug(system.name)}.json"
        results["systems"][system.name] = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    # Model-level measurements, merged across runs (a cached ASR stage was measured by another system).
    results["models"] = model_stats(results["systems"])

    for split in cfg.splits.values():
        split_dir = cfg.split_data_dir(split)
        items = {i["id"]: i for i in read_manifest(split_dir)}
        stats = read_stats(split_dir)
        if stats is not None:
            durations = [audio_info(split_dir / i["audio"]).get("duration_s") for i in items.values()
                         if (split_dir / i["audio"]).exists()]
            durations = [x for x in durations if x is not None]
            if durations:
                stats["mean_duration_s"] = round(sum(durations) / len(durations), 3)
        split_res = {"task": split.task, "n_items": len(items), "stats": stats, "systems": {}}
        for system in cfg.systems.values():
            meta = results["systems"][system.name]
            skipped = meta.get("splits", {}).get(split.name, {}).get("skipped")
            preds = _read_jsonl(cfg.run_dir / split.name / "pred" / f"{slug(system.name)}.jsonl")
            preds = {k: v for k, v in preds.items() if k in items}
            if not preds:
                split_res["systems"][system.name] = {"status": f"skipped: {skipped}" if skipped else "not run"}
                continue
            split_res["systems"][system.name] = _score_system(cfg, split.task, system, results["models"], items, preds)
        results["splits"][split.name] = split_res
    results["gates"] = gate_checks(cfg, results)
    return results


def model_stats(system_metas: dict) -> dict:
    merged: dict = {}
    for meta in system_metas.values():
        for name, m in meta.get("models", {}).items():
            entry = merged.setdefault(name, {})
            for k, v in m.items():
                if v is None:
                    continue
                entry[k] = max(entry[k], v) if k == "peak_memory_gb" and k in entry else v
    return merged


def reference(item: dict) -> str:
    """Raw dataset LaTeX when available. The normalized column carries pipeline artifacts
    (e.g. "\\\\" as a space marker, extra grouping braces) that only the paper's own models reproduce."""
    return item.get("sentence") or item["target"]


def _views(cfg: Config, task: str, ids: list[str], items: dict, preds: dict, ref_fn) -> dict:
    per_item = {i: score_item(preds[i]["pred"], ref_fn(items[i]), task) for i in ids}
    views = {}
    for view in per_item[ids[0]]:
        scores = [per_item[i][view] for i in ids]
        lo, hi = bootstrap_cer_ci(scores, seed=cfg.seed)
        by_group = defaultdict(list)
        for i in ids:
            by_group[items[i]["group"]].append(per_item[i][view])
        views[view] = {**corpus_rates(scores), "cer_ci": [lo, hi], "median_item_cer": median_item_cer(scores),
                       "cer_by_group": {g: corpus_rates(s)["cer"] for g, s in sorted(by_group.items())},
                       "n_by_group": {g: len(s) for g, s in sorted(by_group.items())}}
    return views


def _score_system(cfg: Config, task: str, system: SystemCfg, models: dict, items: dict, preds: dict) -> dict:
    ids = sorted(preds)
    views = _views(cfg, task, ids, items, preds, reference)
    # Sensitivity check: the same scores against the dataset's normalized reference.
    alt = _views(cfg, task, ids, items, preds, lambda it: it["target"])

    text_only = system.asr is not None and system.asr.startswith(COLUMN_PREFIX)
    lat = [preds[i]["gen_s"] if text_only else preds[i]["total_s"] for i in ids]
    lat = [x for x in lat if x is not None]
    pred_texts = [preds[i]["pred"] for i in ids]
    return {
        "status": "ok",
        "n": len(ids),
        "coverage": len(ids) / len(items),
        "nonempty": sum(bool(p.strip()) for p in pred_texts) / len(ids),
        "views": views,
        "headline": views[HEADLINE_VIEW[task]],
        "headline_vs_normalized_ref": alt[HEADLINE_VIEW[task]],
        "render_rate": _render_rate(pred_texts, task),
        "latency_p50_s": percentile(lat, 0.5),
        "latency_p95_s": percentile(lat, 0.95),
        "latency_scope": "text step only (transcript from dataset)" if text_only else "end of audio to LaTeX",
        "peak_memory_gb": _memory(models, system, task),
        "load_s": _load_s(models, system, task),
    }


def gate_checks(cfg: Config, results: dict) -> list[dict]:
    g = cfg.gates
    checks = []
    for system in cfg.systems.values():
        per_split = {n: s["systems"][system.name] for n, s in results["splits"].items()}
        ran = {n: r for n, r in per_split.items() if r.get("status") == "ok"}
        min_nonempty = g.get("min_nonempty_rate", 0.95)
        ok_pipeline = bool(ran) and all(r["nonempty"] >= min_nonempty and r["coverage"] >= 0.999 for r in ran.values())
        checks.append({"system": system.name, "check": "pipeline runs end to end",
                       "pass": ok_pipeline,
                       "detail": ", ".join(f"{n}: {r['n']} items, {_fmt(r['nonempty'], pct=True)} non-empty"
                                           for n, r in ran.items()) or "no predictions"})
        uses_audio = system.e2e or not system.asr.startswith(COLUMN_PREFIX)
        if not uses_audio:
            continue
        mems = [r["peak_memory_gb"] for r in ran.values() if r.get("peak_memory_gb") is not None]
        if "max_peak_memory_gb" in g and mems:
            checks.append({"system": system.name, "check": f"peak memory ≤ {g['max_peak_memory_gb']} GB",
                           "pass": max(mems) <= g["max_peak_memory_gb"], "detail": f"{max(mems):.2f} GB"})
        eq = [r for n, r in ran.items() if results["splits"][n]["task"] == "equations"]
        if "max_p95_latency_s" in g and eq:
            p95 = max(r["latency_p95_s"] for r in eq)
            checks.append({"system": system.name, "check": f"p95 latency ≤ {g['max_p95_latency_s']} s (equations)",
                           "pass": p95 <= g["max_p95_latency_s"], "detail": f"{p95:.2f} s"})
    return checks


def write_report(cfg: Config, results: dict) -> Path:
    out = cfg.run_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    (out / "report.md").write_text(render_markdown(cfg, results))
    (out / "examples.md").write_text(render_examples(cfg))
    return out / "report.md"


def render_markdown(cfg: Config, results: dict) -> str:
    env = next((m.get("environment") for m in results["systems"].values() if m.get("environment")), {}) or {}
    lines = [f"# Run report: {cfg.run_name}", ""]
    if env:
        lines += [f"Machine: {env.get('chip')}, {env.get('memory_gb')} GB, macOS {env.get('macos')}, "
                  f"Python {env.get('python')}. Generated {env.get('timestamp')}.", ""]
    lines += ["CER is corpus-level on normalized LaTeX (see `src/ldbench/metrics.py`), against the dataset's raw "
              "LaTeX (`sentence`); *vs norm. ref* repeats it against the dataset's `sentence_normalized` column. "
              "*Median* is the median per-item CER and *Capped* caps each item's CER at 100%; both are robust to a "
              "single runaway output or refusal. For sentences, *prose WER* is the word error rate on the text outside "
              "$...$ (does the system keep what was said?). Not yet directly "
              "comparable with the paper's published numbers (different normalizer and sample).", ""]

    gates = results["gates"]
    overall = all(c["pass"] for c in gates) if gates else False
    lines += [f"## Gate checks: {'PASS' if overall else 'NOT PASSED'}", "",
              "| System | Check | Result | Detail |", "|---|---|---|---|"]
    lines += [f"| {c['system']} | {c['check']} | {'✅' if c['pass'] else '❌'} | {c['detail']} |" for c in gates]
    lines.append("")

    for name, split in results["splits"].items():
        task = split["task"]
        metric = "CER" if task == "equations" else "equation CER"
        lines += [f"## {name} ({task}, {split['n_items']} items)", ""]
        groups = sorted({g for r in split["systems"].values() if r.get("status") == "ok"
                         for g in r["headline"]["cer_by_group"]})
        head = ["System", "n", f"{metric} (95% CI)", "Median", "Capped", "vs norm. ref",
                *[f"{metric} {g}" for g in groups], "Exact", "Renders", "Latency p50 / p95 (s)", "Peak mem (GB)", "Load (s)"]
        if task == "sentences":
            head.insert(6, "full-text CER")
            head.insert(7, "prose WER")
        lines += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for sys_name, r in split["systems"].items():
            if r.get("status") != "ok":
                lines.append(f"| {sys_name} | {r.get('status')} |" + " |" * (len(head) - 2))
                continue
            h = r["headline"]
            row = [sys_name, str(r["n"]),
                   f"{_fmt(h['cer'], pct=True)} ({_fmt(h['cer_ci'][0], pct=True)}–{_fmt(h['cer_ci'][1], pct=True)})",
                   _fmt(h["median_item_cer"], pct=True), _fmt(h["capped_cer"], pct=True),
                   _fmt(r["headline_vs_normalized_ref"]["cer"], pct=True),
                   *[_fmt(h["cer_by_group"].get(g), pct=True) for g in groups],
                   _fmt(h["exact"], pct=True), _fmt(r["render_rate"], pct=True),
                   f"{_fmt(r['latency_p50_s'])} / {_fmt(r['latency_p95_s'])}"
                   + ("*" if r["latency_scope"].startswith("text") else ""),
                   _fmt(r["peak_memory_gb"]), _fmt(r["load_s"], digits=1)]
            if task == "sentences":
                row.insert(6, _fmt(r["views"]["full"]["cer"], pct=True))
                row.insert(7, _fmt(r["views"]["prose"]["ter"], pct=True))
            lines.append("| " + " | ".join(row) + " |")
        lines += ["", "\\* latency of the text step only (the transcript comes from the dataset).", ""]

    lines += ["## Data", ""]
    for name, split in results["splits"].items():
        stats = split.get("stats") or {}
        lines += [f"### {name}", "", "```json", json.dumps(stats, indent=2, ensure_ascii=False)[:4000], "```", ""]

    lines += ["## Models", "", "| Model | Kind | Repo @ commit | Load (s) | Peak mem (GB) |", "|---|---|---|---|---|"]
    for name, m in sorted(results["models"].items()):
        lines.append(f"| {name} | {m.get('kind')} | `{m.get('repo')}@{str(m.get('sha'))[:10]}` | "
                     f"{_fmt(m.get('load_s'), digits=1)} | {_fmt(m.get('peak_memory_gb'))} |")
    lines.append("")
    return "\n".join(lines)


def render_examples(cfg: Config, per_split: int = 6) -> str:
    """A few random items per split, all systems side by side, for eyeballing."""
    lines = [f"# Examples: {cfg.run_name}", ""]
    rng = random.Random(cfg.seed)
    for split in cfg.splits.values():
        items = read_manifest(cfg.split_data_dir(split))
        if not items:
            continue
        preds = {s: _read_jsonl(cfg.run_dir / split.name / "pred" / f"{slug(s)}.jsonl") for s in cfg.systems}
        lines += [f"## {split.name}", ""]
        for item in rng.sample(items, min(per_split, len(items))):
            lines += [f"### {item['id']} ({item['group']})", "", f"- **reference:** `{item['target']}`"]
            if item.get("whisper_text"):
                lines.append(f"- dataset Whisper transcript: {item['whisper_text']}")
            for s, p in preds.items():
                if item["id"] in p:
                    rec = p[item["id"]]
                    lines.append(f"- **{s}:** `{rec['pred']}`")
                    if rec.get("transcript") and not cfg.systems[s].asr.startswith(COLUMN_PREFIX):
                        lines.append(f"  - transcript: {rec['transcript']}")
            lines.append("")
    return "\n".join(lines)
