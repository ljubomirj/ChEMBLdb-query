import os


def pytest_configure() -> None:
    os.environ.setdefault("COLUMNS", "20")
