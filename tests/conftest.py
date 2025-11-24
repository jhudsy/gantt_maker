import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Provide a shared QApplication for tests that instantiate widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
