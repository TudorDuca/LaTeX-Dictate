"""Push-to-talk maths dictation: hold a hotkey, speak, release -> LaTeX on the clipboard (and pasted).

Models stay loaded, so each dictation costs only inference (~1 s for Whisper-turbo + the paper's model).
All MLX work happens on the main thread; the hotkey listener and the microphone callback only
post events and audio chunks.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import tempfile
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

from .backends import ASR_KINDS, E2E_KINDS, TEXT_KINDS
from .config import COLUMN_PREFIX, Config
from .postprocess import clean_output
from .prompts import e2e_prompt, text_messages
from .runner import ModelPool

MIN_SECONDS = 0.3
SOUNDS = {"start": "Tink", "stop": "Pop", "error": "Basso"}
WRAPS = {"none": "{}", "inline": "${}$", "display": "\\[{}\\]"}


# --------------------------------------------------------------------------- models


def max_tokens_for(transcript: str, cap: int) -> int:
    """Bound generation by the length of what was said, so a repetition loop stays short."""
    return min(cap, 32 + 6 * len(transcript.split()))


class Pipeline:
    """Audio file -> LaTeX with one benchmark system's models, loaded once."""

    def __init__(self, cfg: Config, system_name: str, task: str):
        if system_name not in cfg.systems:
            raise SystemExit(f"unknown system {system_name!r}; choose from {sorted(cfg.systems)}")
        self.system = cfg.systems[system_name]
        self.task = task
        if self.system.asr and self.system.asr.startswith(COLUMN_PREFIX):
            raise SystemExit(f"{system_name} reads transcripts from the dataset; pick a system with a real ASR model")
        self.pool = ModelPool(cfg, {"models": {}})
        self.e2e = self.asr = self.text = None
        if self.system.e2e:
            self.e2e = self.pool.get(self.system.e2e, E2E_KINDS)
        else:
            self.asr = self.pool.get(self.system.asr, ASR_KINDS)
            text_name = self.system.text_model_for(task)
            self.text = self.pool.get(text_name, TEXT_KINDS) if text_name else None

    def warm_up(self, wav_path: str) -> None:
        if self.e2e:
            self.e2e.generate(wav_path, e2e_prompt(self.task), 8)
            return
        self.asr.transcribe(wav_path)
        if self.text:
            self.text.generate(text_messages(self.system.prompt, self.task, "x squared"), 8)

    def __call__(self, wav_path: str) -> dict:
        t0 = time.perf_counter()
        if self.e2e:
            raw = self.e2e.generate(wav_path, e2e_prompt(self.task), self.system.max_tokens)
            return {"transcript": None, "raw": raw, "latex": clean_output(raw, self.task),
                    "asr_s": None, "gen_s": time.perf_counter() - t0}
        transcript = self.asr.transcribe(wav_path)
        t1 = time.perf_counter()
        if not transcript.strip():
            return {"transcript": transcript, "raw": "", "latex": "", "asr_s": t1 - t0, "gen_s": 0.0}
        if self.text is None:
            raw = transcript
        else:
            messages = text_messages(self.system.prompt, self.task, transcript)
            raw = self.text.generate(messages, max_tokens_for(transcript, self.system.max_tokens))
        return {"transcript": transcript, "raw": raw, "latex": clean_output(raw, self.task),
                "asr_s": t1 - t0, "gen_s": time.perf_counter() - t1}


# --------------------------------------------------------------------------- audio


class Recorder:
    def __init__(self, device: str | None = None):
        import sounddevice as sd

        self.sd = sd
        self.device = int(device) if device and device.isdigit() else device
        self.rate = int(sd.query_devices(self.device, kind="input")["default_samplerate"])
        self.chunks: list = []
        self.stream = None

    def start(self) -> None:
        self.chunks = []
        self.stream = self.sd.InputStream(samplerate=self.rate, channels=1, dtype="int16", device=self.device,
                                          callback=lambda data, frames, t, status: self.chunks.append(data.copy()))
        self.stream.start()

    def stop(self) -> list:
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        return self.chunks


def write_wav(path: Path, chunks: list, rate: int) -> float:
    import numpy as np

    audio = np.concatenate(chunks) if chunks else np.zeros((0, 1), dtype="int16")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(audio.tobytes())
    return len(audio) / rate


# --------------------------------------------------------------------------- hotkeys


# macOS virtual key codes (kVK_ANSI_*) for letters and digits. With Option held, macOS reports the
# composed character (Option+M -> "µ"), so letters in a hotkey are matched by physical key as well.
MAC_ANSI_VK = {
    "a": 0x00, "s": 0x01, "d": 0x02, "f": 0x03, "h": 0x04, "g": 0x05, "z": 0x06, "x": 0x07, "c": 0x08,
    "v": 0x09, "b": 0x0B, "q": 0x0C, "w": 0x0D, "e": 0x0E, "r": 0x0F, "y": 0x10, "t": 0x11, "1": 0x12,
    "2": 0x13, "3": 0x14, "4": 0x15, "6": 0x16, "5": 0x17, "9": 0x19, "7": 0x1A, "8": 0x1C, "0": 0x1D,
    "o": 0x1F, "u": 0x20, "i": 0x22, "p": 0x23, "l": 0x25, "j": 0x26, "k": 0x28, "n": 0x2D, "m": 0x2E,
}


def key_matches(pressed_key, combo_key, canonical) -> bool:
    """True if a pressed key satisfies one part of a parsed hotkey.

    pynput's canonical() merges left/right modifiers, so '<ctrl>' matches either ctrl key; an
    explicit side such as '<alt_r>' parses to the key's virtual-key code and is matched exactly.
    """
    if pressed_key == combo_key or canonical(pressed_key) == combo_key:
        return True
    value = getattr(pressed_key, "value", None)  # Key enum members wrap a KeyCode
    if value is not None and value == combo_key:
        return True
    char, vk = getattr(combo_key, "char", None), getattr(pressed_key, "vk", None)
    return bool(char) and vk is not None and MAC_ANSI_VK.get(char.lower()) == vk


class HoldDetector:
    """Turns raw key presses/releases into 'start' (combo fully held) and 'stop' (combo released)."""

    def __init__(self, combo: list, canonical, emit):
        self.combo, self.canonical, self.emit = combo, canonical, emit
        self.pressed: dict = {}  # physical key -> last event for it
        self.active = False

    @staticmethod
    def _ident(key):
        """Physical identity: the same key can arrive as "µ" on press and "m" on release."""
        vk = getattr(key, "vk", None)
        if vk is None:
            vk = getattr(getattr(key, "value", None), "vk", None)
        return ("vk", vk) if vk is not None else key

    def _held(self) -> bool:
        return all(any(key_matches(p, c, self.canonical) for p in self.pressed.values()) for c in self.combo)

    def press(self, key) -> None:
        self.pressed[self._ident(key)] = key
        if not self.active and self._held():
            self.active = True
            self.emit("start")

    def release(self, key) -> None:
        self.pressed.pop(self._ident(key), None)
        if self.active and any(key_matches(key, c, self.canonical) for c in self.combo):
            self.active = False
            self.emit("stop")


def start_hotkey_listener(mode: str, hotkey: str, emit) -> object:
    """Global key listener. Toggle mode reuses the hold detector: each time the combo becomes held."""
    from pynput import keyboard

    combo = keyboard.HotKey.parse(hotkey)
    holder: dict = {}
    if mode == "toggle":
        def on_event(event: str) -> None:
            if event == "start":
                emit("toggle")
    else:
        on_event = emit
    detector = HoldDetector(combo, lambda k: holder["l"].canonical(k), on_event)
    listener = keyboard.Listener(on_press=detector.press, on_release=detector.release)
    holder["l"] = listener
    listener.daemon = True
    listener.start()
    return listener


def start_terminal_listener(emit) -> None:
    def loop():
        while True:
            try:
                input()
            except EOFError:
                emit("quit")
                return
            emit("toggle")

    threading.Thread(target=loop, daemon=True).start()


# --------------------------------------------------------------------------- output


def copy_to_clipboard(text: str) -> None:
    env = {**os.environ, "LANG": os.environ.get("LANG", "en_US.UTF-8")}
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), env=env, check=True)


def paste() -> None:
    from pynput.keyboard import Controller, Key

    kb = Controller()
    time.sleep(0.05)  # let the hotkey's own key-up reach the app first
    with kb.pressed(Key.cmd):
        kb.press("v")
        kb.release("v")


def play(sound: str) -> None:
    path = f"/System/Library/Sounds/{SOUNDS[sound]}.aiff"
    if os.path.exists(path):
        subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --------------------------------------------------------------------------- main loop


class Dictation:
    """Event loop on the main thread: start/stop recording, run the pipeline, deliver the LaTeX."""

    def __init__(self, pipeline, recorder, *, wrap: str = "none", do_paste: bool = False, sounds: bool = True,
                 log_path: Path | None = None, audio_dir: Path | None = None,
                 clipboard=copy_to_clipboard, paster=paste, player=play, out=print):
        self.pipeline, self.recorder = pipeline, recorder
        self.wrap, self.do_paste, self.sounds = wrap, do_paste, sounds
        self.log_path, self.audio_dir = log_path, audio_dir
        self.clipboard, self.paster, self.player, self.out = clipboard, paster, player, out
        self.events: queue.Queue = queue.Queue()
        self.recording = False

    def emit(self, event: str) -> None:
        self.events.put(event)

    def _sound(self, name: str) -> None:
        if self.sounds:
            self.player(name)

    def handle(self, event: str) -> bool:
        """Process one event; returns False to quit."""
        if event == "quit":
            return False
        if event == "toggle":
            event = "stop" if self.recording else "start"
        if event == "start" and not self.recording:
            self.recorder.start()
            self.recording = True
            self._sound("start")
            self.out("● listening… (release to convert)")
        elif event == "stop" and self.recording:
            chunks = self.recorder.stop()
            self.recording = False
            self._sound("stop")
            self._process(chunks)
        return True

    def _process(self, chunks: list) -> dict | None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if self.audio_dir is not None:
            wav = self.audio_dir / f"{stamp}.wav"
        else:
            wav = Path(tempfile.gettempdir()) / f"ldb-dictate-{os.getpid()}.wav"
        seconds = write_wav(wav, chunks, self.recorder.rate)
        if seconds < MIN_SECONDS:
            self.out("  (too short, ignored)")
            return None
        try:
            result = self.pipeline(str(wav))
        except Exception as e:  # keep the daemon alive on a bad take
            self._sound("error")
            self.out(f"  ! failed: {type(e).__name__}: {e}")
            return None
        latex = result["latex"]
        if not latex:
            self._sound("error")
            self.out(f"  ! nothing recognised (heard: {result['transcript']!r})")
        else:
            text = WRAPS[self.wrap].format(latex)
            self.clipboard(text)
            if self.do_paste:
                self.paster()
            timing = f"{(result['asr_s'] or 0) + result['gen_s']:.2f} s"
            if result["transcript"] is not None:
                self.out(f"  heard: {result['transcript']}")
            self.out(f"  LaTeX: {text}   [{timing}{', pasted' if self.do_paste else ', copied'}]")
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a") as f:
                f.write(json.dumps({"time": stamp, "seconds": round(seconds, 2),
                                    "audio": str(wav) if self.audio_dir is not None else None,
                                    **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in result.items()}},
                                   ensure_ascii=False) + "\n")
        return result

    def run(self) -> None:
        try:
            while True:
                try:
                    event = self.events.get(timeout=0.25)  # short timeout keeps Ctrl+C responsive
                except queue.Empty:
                    continue
                if not self.handle(event):
                    break
        except KeyboardInterrupt:
            pass
        finally:
            if self.recording:
                self.recorder.stop()


# --------------------------------------------------------------------------- entry point

DEFAULT_HOTKEYS = {"hold": "<alt_r>", "toggle": "<ctrl>+<alt>+m"}

UNTRUSTED = """\
  ! macOS is not letting this terminal see global key presses.
    System Settings > Privacy & Security > Accessibility (and Input Monitoring):
    enable your terminal app (Terminal, iTerm, VS Code...), then restart it.
    Meanwhile you can use:  ldb dictate --mode terminal   (Enter in this window starts/stops)
"""


def main(cfg: Config, system: str, task: str, mode: str, hotkey: str | None, wrap: str, do_paste: bool,
         device: str | None, save_audio: bool, sounds: bool) -> None:
    from .record import OPEN_FAILED

    print(f"Loading {system} ({task})…", flush=True)
    t0 = time.perf_counter()
    pipeline = Pipeline(cfg, system, task)
    silence = Path(tempfile.gettempdir()) / "ldb-dictate-warmup.wav"
    import numpy as np

    write_wav(silence, [np.zeros((16_000, 1), dtype="int16")], 16_000)
    pipeline.warm_up(str(silence))
    print(f"Ready in {time.perf_counter() - t0:.1f} s.", flush=True)

    try:
        recorder = Recorder(device)
    except Exception as e:  # noqa: BLE001 - PortAudio errors are not importable without sounddevice
        raise SystemExit(OPEN_FAILED.format(error=e, audio_dir="data/own/audio")) from e

    run_dir = cfg.runs_dir / "dictate"
    dictation = Dictation(
        pipeline, recorder, wrap=wrap, do_paste=do_paste, sounds=sounds,
        log_path=run_dir / "log.jsonl",
        audio_dir=(cfg.data_dir / "dictations" / "audio") if save_audio else None,
    )

    hotkey = hotkey or DEFAULT_HOTKEYS.get(mode)
    if mode == "terminal":
        start_terminal_listener(dictation.emit)
        how = "Press Enter here to start, Enter again to convert."
    else:
        listener = start_hotkey_listener(mode, hotkey, dictation.emit)
        if getattr(listener, "IS_TRUSTED", True) is False:
            print(UNTRUSTED)
        how = (f"Hold {hotkey}, speak, release." if mode == "hold"
               else f"Press {hotkey} to start, press it again to convert.")
    target = "pasted into the focused app" if do_paste else "copied to the clipboard"
    print(f"{how} The LaTeX is {target}. Ctrl+C quits.\nInput: {recorder.sd.query_devices(recorder.device, kind='input')['name']}"
          f" ({recorder.rate} Hz). Log: {run_dir / 'log.jsonl'}\n", flush=True)
    dictation.run()
