from pathlib import Path


def write_placeholder(dataset_name: str, payload: list[dict], output_dir: str) -> str:
    target = Path(output_dir) / f"{dataset_name}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(payload), encoding="utf-8")
    return str(target)
