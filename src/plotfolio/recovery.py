"""Atomic, local recovery snapshots; never overwrite a source/project file."""

import json
import os
import time
from pathlib import Path


def write_snapshot(directory, session, doc, filename=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"recovery-{session}.json"
    temporary = path.with_suffix(".tmp")
    content = dict(
        recovery_version=1, pid=os.getpid(), timestamp=time.time(), filename=filename, document=doc
    )
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(content, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    return path


def read_snapshot(path):
    content = json.loads(Path(path).read_text(encoding="utf-8"))
    if content.get("recovery_version") != 1 or content.get("document", {}).get("version") != 2:
        raise ValueError("Unsupported recovery snapshot.")
    return content


def candidates(directory):
    found = []
    for path in Path(directory).glob("recovery-*.json"):
        try:
            content = read_snapshot(path)
            try:
                os.kill(int(content["pid"]), 0)
            except (ProcessLookupError, ValueError, KeyError):
                found.append((path, content))
            except PermissionError:
                continue
        except (OSError, ValueError):
            continue
    return sorted(found, key=lambda item: item[1]["timestamp"], reverse=True)
