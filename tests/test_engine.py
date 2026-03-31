import os
import dawsmith
import pytest

VST_PATH = os.path.join(os.path.dirname(__file__), "..", "vsts")


def test_engine_creates():
    engine = dawsmith.create_engine()
    assert engine is not None


def test_engine_creates_with_custom_name():
    engine = dawsmith.create_engine("TestApp")
    assert engine is not None


def test_plugin_scan_finds_dexed(engine_with_plugins):
    plugins = engine_with_plugins.get_available_plugins()
    names = [p.name for p in plugins]
    assert any("Dexed" in name for name in names), (
        f"Dexed not found. Available: {names}"
    )


def test_get_available_plugins_returns_descriptions(engine_with_plugins):
    plugins = engine_with_plugins.get_available_plugins()
    assert len(plugins) > 0
    p = plugins[0]
    assert isinstance(p.name, str) and len(p.name) > 0
    assert isinstance(p.manufacturer, str)
    assert isinstance(p.identifier, str) and len(p.identifier) > 0
    assert isinstance(p.format, str)
    assert isinstance(p.is_instrument, bool)


def test_available_plugins_has_instruments(engine_with_plugins):
    plugins = engine_with_plugins.get_available_plugins()
    instruments = [p for p in plugins if p.is_instrument]
    assert len(instruments) > 0, "No instrument plugins found"
