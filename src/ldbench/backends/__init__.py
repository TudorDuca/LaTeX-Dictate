"""Model backends. Each kind maps a model config to an object with one inference method.

- ASR:  ``transcribe(audio_path) -> str``
- Text: ``generate(messages, max_tokens) -> str``
- E2E:  ``generate(audio_path, prompt, max_tokens) -> str``

Heavy libraries (MLX and friends) are imported only when a backend is constructed, so the
harness itself (data, metrics, reports, tests) runs anywhere.
"""

from __future__ import annotations

from typing import Callable

from ..config import ModelCfg

ASR_KINDS: dict[str, Callable] = {}
TEXT_KINDS: dict[str, Callable] = {}
E2E_KINDS: dict[str, Callable] = {}


def register(table: dict[str, Callable], kind: str):
    def deco(factory: Callable) -> Callable:
        table[kind] = factory
        return factory

    return deco


def create(table: dict[str, Callable], model: ModelCfg, local_path: str):
    if model.kind not in table:
        raise ValueError(f"model {model.name}: kind {model.kind!r} not usable here (known: {sorted(table)})")
    return table[model.kind](model, local_path)


from . import mlx as _mlx  # noqa: E402,F401  (registers the MLX kinds)
