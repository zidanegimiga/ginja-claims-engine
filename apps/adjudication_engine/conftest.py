import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(__file__))

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"