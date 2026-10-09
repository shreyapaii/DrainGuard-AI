"""Pytest safety defaults for Windows environments with locked user temp folders."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def pytest_configure(config):
    """Keep pytest temporary files inside the project workspace."""
    project_tmp = Path(__file__).resolve().parent / ".tmp"
    project_tmp.mkdir(exist_ok=True)
    os.environ["TMP"] = str(project_tmp)
    os.environ["TEMP"] = str(project_tmp)
    tempfile.tempdir = str(project_tmp)
    if getattr(config.option, "basetemp", None) is None:
        config.option.basetemp = str(project_tmp)
