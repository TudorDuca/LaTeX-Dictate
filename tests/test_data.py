from collections import Counter
from pathlib import Path

from ldbench.data import (
    build_local_manifest,
    fetch_parquet_sample,
    read_manifest,
    sniff_audio_ext,
    strip_math_delimiters,
)

from .conftest import make_wav


def test_parquet_sample_respects_quota_language_and_spread(parquet_split, tmp_path: Path):
    out = tmp_path / "eq"
    stats = fetch_parquet_sample(parquet_split, lambda p: open(p, "rb"), out, "equations", "equations",
                                 "eng", {"human": 5, "tts": 5}, seed=1, max_per_row_group=2)
    items = read_manifest(out)
    assert Counter(i["group"] for i in items) == {"human": 5, "tts": 5}
    assert all(i["language"] == "eng" for i in items)
    assert all((out / i["audio"]).exists() and i["format"] == "wav" for i in items)
    assert all(i["duration_s"] == 0.5 for i in items)
    # target is the normalized column without math delimiters; text columns are carried over
    assert all(i["target"].startswith("x^{") and i["pronunciation"] for i in items)
    # spread: no row group contributes more than the cap
    per_rg = Counter(i["source"].split(":")[0] for i in items)
    assert max(per_rg.values()) <= 2
    assert stats["rows_total"] == 60
    assert stats["rows_by_language_group"] == {"eng/human": 20, "eng/tts": 20, "ru/human": 10, "ru/tts": 10}
    assert stats["audio_column"] == "audio_path"


def test_parquet_sample_is_deterministic(parquet_split, tmp_path: Path):
    def ids(seed, name):
        fetch_parquet_sample(parquet_split, lambda p: open(p, "rb"), tmp_path / name, "e", "equations",
                             "eng", {"human": 5}, seed=seed, max_per_row_group=4)
        return [i["source"] for i in read_manifest(tmp_path / name)]

    assert ids(3, "a") == ids(3, "b")
    assert ids(3, "a") != ids(4, "c")


def test_small_group_relaxes_row_group_cap(parquet_split, tmp_path: Path):
    fetch_parquet_sample(parquet_split, lambda p: open(p, "rb"), tmp_path / "x", "e", "equations",
                         "ru", {"human": 10}, seed=0, max_per_row_group=1)
    assert len(read_manifest(tmp_path / "x")) == 10


def test_local_manifest_includes_only_recorded(tmp_path: Path):
    (tmp_path / "formulas.csv").write_text("id,difficulty,latex\nf01,easy,x^{2}\nf02,easy,$y$\n")
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "f02.wav").write_bytes(make_wav())
    stats = build_local_manifest(tmp_path)
    items = read_manifest(tmp_path)
    assert [i["id"] for i in items] == ["f02"] and items[0]["target"] == "y"
    assert stats["missing_recordings"] == ["f01"]


def test_helpers():
    assert sniff_audio_ext(make_wav()) == "wav"
    assert sniff_audio_ext(b"fLaC....") == "flac"
    assert strip_math_delimiters("$$ a $$") == "a"
    assert strip_math_delimiters("a $b$") == "a $b$"
