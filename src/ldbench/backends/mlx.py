"""Apple Silicon backends built on MLX: mlx-whisper, mlx-lm and mlx-audio."""

from __future__ import annotations

from ..config import ModelCfg
from . import ASR_KINDS, E2E_KINDS, TEXT_KINDS, register


@register(ASR_KINDS, "mlx-whisper")
class MlxWhisper:
    def __init__(self, model: ModelCfg, local_path: str):
        import mlx.core as mx
        from mlx_whisper.transcribe import ModelHolder

        self.path = local_path
        self.options = {
            "language": "en",
            "temperature": 0.0,
            "condition_on_previous_text": False,
            **model.options,
        }
        ModelHolder.get_model(local_path, mx.float16)  # load now so load time is measured

    def set_language(self, language: str) -> None:
        from ..languages import to_code

        code = to_code(language)
        if code is None:
            self.options.pop("language", None)  # Whisper detects the language
        else:
            self.options["language"] = code

    def transcribe(self, audio_path: str) -> str:
        import mlx_whisper

        return mlx_whisper.transcribe(audio_path, path_or_hf_repo=self.path, **self.options)["text"].strip()


@register(ASR_KINDS, "mlx-audio-stt")
class MlxAudioSTT:
    """Any mlx-audio speech-to-text model (Parakeet, Qwen3-ASR, ...), plain transcription."""

    def __init__(self, model: ModelCfg, local_path: str):
        from mlx_audio.stt import load

        self.model = load(local_path)
        self.options = dict(model.options)

    def set_language(self, language: str) -> None:
        """For models that take a language name (e.g. Qwen3-ASR); others ignore it."""
        import inspect

        from ..languages import to_name

        if "language" not in inspect.signature(self.model.generate).parameters:
            return
        name = to_name(language)
        if name is None:
            self.options.pop("language", None)
        else:
            self.options["language"] = name

    def transcribe(self, audio_path: str) -> str:
        return self.model.generate(audio_path, **self.options).text.strip()


@register(TEXT_KINDS, "mlx-lm")
class MlxLM:
    def __init__(self, model: ModelCfg, local_path: str):
        from mlx_lm import load

        self.model, self.tokenizer = load(local_path)
        self.options = dict(model.options)

    def generate(self, messages: list[dict], max_tokens: int) -> str:
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler

        prompt = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        return generate(
            self.model,
            self.tokenizer,
            prompt,
            max_tokens=max_tokens,
            sampler=make_sampler(temp=0.0),
            verbose=False,
        )


@register(E2E_KINDS, "mlx-audio-chat")
class MlxAudioChat:
    """Audio-language models in mlx-audio that accept an instruction (e.g. Qwen2-Audio)."""

    def __init__(self, model: ModelCfg, local_path: str):
        from mlx_audio.stt import load

        self.model = load(local_path)
        self.options = dict(model.options)

    def generate(self, audio_path: str, prompt: str, max_tokens: int) -> str:
        out = self.model.generate(
            audio_path, prompt=prompt, max_tokens=max_tokens, temperature=0.0, **self.options
        )
        return out.text


def peak_memory_gb() -> float | None:
    try:
        import mlx.core as mx
    except ImportError:
        return None
    return mx.get_peak_memory() / 1e9


def reset_peak_memory() -> None:
    try:
        import mlx.core as mx
    except ImportError:
        return
    mx.reset_peak_memory()


def free_memory() -> None:
    import gc

    gc.collect()
    try:
        import mlx.core as mx
    except ImportError:
        return
    mx.clear_cache()
