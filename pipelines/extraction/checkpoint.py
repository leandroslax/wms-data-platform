from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import boto3


@dataclass
class ExtractionCheckpoint:
    entity_name: str
    last_value: str | None = None


def write_checkpoint(bucket: str, entity_name: str, last_value: str | None) -> None:
    s3 = boto3.client("s3")
    payload = asdict(ExtractionCheckpoint(entity_name=entity_name, last_value=last_value))
    s3.put_object(
        Bucket=bucket,
        Key=f"checkpoints/{entity_name}.json",
        Body=json.dumps(payload).encode("utf-8"),
        ContentType="application/json",
    )
