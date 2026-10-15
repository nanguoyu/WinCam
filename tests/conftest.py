import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def qapp():
    from wincam.app import create_app

    return create_app([])


@pytest.fixture
def config(tmp_path, qapp):
    from PySide6.QtCore import QSettings

    from wincam.config import Config

    return Config(QSettings(str(tmp_path / "test.ini"), QSettings.Format.IniFormat))
