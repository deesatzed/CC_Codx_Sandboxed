import json
from pathlib import Path

MODEL_DIR = Path(
    "/Volumes/WS4TB/q38Ablit/models/PocketAiHub--Qwen3.8-27B-Abliterated-MLX/4bit"
)


def test_4bit_index_and_shards_exist():
    index = MODEL_DIR / "model.safetensors.index.json"
    assert index.is_file(), f"missing {index}"
    data = json.loads(index.read_text())
    names = sorted(set((data.get("weight_map") or {}).values()))
    assert names, "weight_map empty"
    missing = [n for n in names if not (MODEL_DIR / n).is_file() or (MODEL_DIR / n).stat().st_size <= 0]
    assert missing == [], f"missing shards: {missing}"


def test_tokenizer_and_config_exist():
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json"):
        assert (MODEL_DIR / name).is_file(), name
