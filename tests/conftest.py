import os
import pytest
import dawsmith

VST_PATH = os.path.join(os.path.dirname(__file__), "..", "vsts")


@pytest.fixture(scope="session")
def engine():
    """Create a DAWsmith engine for the entire test session."""
    return dawsmith.create_engine()


@pytest.fixture(scope="session")
def engine_with_plugins(engine):
    """Engine with VST plugins scanned from vsts/ directory."""
    if os.path.isdir(VST_PATH):
        engine.scan_plugins(VST_PATH)
    return engine


@pytest.fixture(scope="session")
def first_instrument(engine_with_plugins):
    """The first instrument plugin found, or skip if none available."""
    plugins = engine_with_plugins.get_available_plugins()
    instruments = [p for p in plugins if p.is_instrument]
    if not instruments:
        pytest.skip("No instrument plugins found in vsts/")
    return instruments[0]
