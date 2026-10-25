import io
import wave
from pathlib import Path

import pytest


def make_wav(seconds: float = 0.5, rate: int = 16_000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buf.getvalue()


@pytest.fixture
def parquet_split(tmp_path: Path):
    """Two parquet files shaped like Speech2Latex: an Audio struct column plus text metadata."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    wav = make_wav()
    files = []
    k = 0
    for f in range(2):
        rows = []
        for _ in range(30):
            lang = "eng" if k % 3 else "ru"
            rows.append({
                "audio_path": {"bytes": wav, "path": f"clip{k}.wav"},
                "sentence": f"$x^{{{k}}}$",
                "sentence_normalized": f"x^{{{k}}}",
                "pronunciation": f"x to the power {k}",
                "whisper_text": f"x to the power {k}.",
                "is_tts": k % 2,
                "language": lang,
            })
            k += 1
        path = tmp_path / f"equations_test-0000{f}-of-00002.parquet"
        pq.write_table(pa.Table.from_pylist(rows), path, row_group_size=10)
        files.append(str(path))
    return files
