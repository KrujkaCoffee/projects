from __future__ import annotations

from pathlib import Path

from PyQt5 import uic


UI_DIR = Path(__file__).resolve().parent / "ui"


def ui_path(name: str) -> str:
    return str(UI_DIR / name)


def load_ui(name: str, baseinstance):
    return uic.loadUi(ui_path(name), baseinstance)
