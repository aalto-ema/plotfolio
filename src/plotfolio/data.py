"""CSV and image ingestion; never mutate original source data."""

import base64
import csv
import io
import math
from pathlib import Path

import numpy as np
from PIL import Image


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(16384)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(f, dialect)
        headers = next(reader, [])
        if not headers or any(not h.strip() for h in headers) or len(set(headers)) != len(headers):
            raise ValueError("CSV needs unique, nonempty column headers.")
        rows = []
        for line, row in enumerate(reader, 2):
            if not row:
                continue
            if len(row) != len(headers):
                raise ValueError(
                    f"CSV row {line}: expected {len(headers)} cells, found {len(row)}."
                )
            rows.append(row)
    if not rows:
        raise ValueError("CSV has no data rows.")
    return dict(name=Path(path).name, headers=headers, rows=rows, source=str(Path(path).resolve()))


def numeric(values):
    out = []
    for value in values:
        try:
            out.append(float(value))
        except (ValueError, TypeError):
            out.append(np.nan)
    return np.asarray(out)


def columns(dataset):
    return {h: [r[i] for r in dataset["rows"]] for i, h in enumerate(dataset["headers"])}


def numeric_columns(dataset):
    return [k for k, v in columns(dataset).items() if np.isfinite(numeric(v)).any()]


def ratios(text, count):
    if not str(text).strip():
        return [1] * count
    values = [float(v) for v in str(text).replace(",", ":").split(":")]
    if len(values) != count or any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError(f"Provide {count} positive ratios, e.g. " + ":".join(["1"] * count))
    return values


def image_payload(path):
    # Decode once on import; preserve pixel data without external file dependencies.
    with Image.open(path) as image:
        image.load()
        stream = io.BytesIO()
        image.convert("RGBA").save(stream, format="PNG")
    return base64.b64encode(stream.getvalue()).decode("ascii")


def image_array(payload):
    with Image.open(io.BytesIO(base64.b64decode(payload))) as image:
        return np.asarray(image.convert("RGBA"))
