from pathlib import Path

import pytest

from ldbench.config import load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["m0.toml", "smoke.toml"])
def test_shipped_configs_load(name):
    cfg = load_config(ROOT / "configs" / name)
    assert cfg.systems and cfg.models and cfg.splits
    for system in cfg.systems.values():
        for split in cfg.splits.values():
            if system.text is not None:
                assert system.text_model_for(split.task) in cfg.models


def test_unknown_model_is_rejected(tmp_path):
    (tmp_path / "configs").mkdir()
    p = tmp_path / "configs" / "bad.toml"
    p.write_text('run_name="x"\n[[systems]]\nname="s"\nasr="nope"\n')
    with pytest.raises(ValueError, match="unknown asr model"):
        load_config(p)
