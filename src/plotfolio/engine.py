"""Convenience API; implementations live in focused, Qt-independent modules."""

from .constants import CMAPS, COLORS, KINDS, SOURCES, TEMPLATES
from .data import columns, image_array, image_payload, numeric, numeric_columns, ratios, read_csv
from .examples import demo_document
from .model import annotation, document, panel, series, settings
from .projects import load_project, save_project
from .rendering import build_figure

__all__ = [
    "COLORS",
    "CMAPS",
    "KINDS",
    "TEMPLATES",
    "SOURCES",
    "settings",
    "series",
    "panel",
    "document",
    "annotation",
    "read_csv",
    "numeric",
    "columns",
    "numeric_columns",
    "ratios",
    "image_payload",
    "image_array",
    "build_figure",
    "save_project",
    "load_project",
    "demo_document",
]
